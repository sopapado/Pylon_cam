"""Small public API derived from Pylon_init.py's configuration workflow."""
import math
import numbers
import threading

from ._driver import Driver
from .errors import PicamError


def integer(value, name, minimum=1):
    if isinstance(value, bool) or not isinstance(value, numbers.Integral) or value < minimum:
        raise ValueError('{} must be an integer >= {}'.format(name, minimum))
    return int(value)


class Camera:
    """First available physical camera. Use as a context manager or call close().

    Constructor is inert; entering the context or calling open() connects.
    One camera session per process; calls on an instance are serialized.
    """

    def __init__(self, dll_path=None):
        self._driver = Driver(dll_path)
        self._opened = False
        self._configured = False
        self._settings = None
        self._lock = threading.RLock()

    def open(self):
        with self._lock:
            if not self._opened:
                self._driver.open()
                self._opened = True
            return self

    def close(self):
        with self._lock:
            try:
                self._driver.close()
            finally:
                self._opened = self._configured = False

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, tb):
        with self._lock:
            try:
                self._driver.close(suppress=exc_type is not None)
            finally:
                self._opened = self._configured = False
        return False

    def _require_open(self):
        if not self._opened:
            raise PicamError('Camera is closed; use with Camera() as cam or cam.open()')

    @property
    def temperature_c(self):
        """Sensor temperature in degrees Celsius (read-only)."""
        with self._lock:
            self._require_open()
            return self._driver.temperature()

    def configure(self, exposure_ms=100, y_start=0, y_height=None, y_binning=None):
        """Set full-width ROI. None height uses remaining sensor rows;
        None binning bins all selected rows into one spectrum.
        Use y_binning=1 for an image. SDK commit validates hardware constraints.
        """
        with self._lock:
            self._require_open()
            if (isinstance(exposure_ms, bool) or not isinstance(exposure_ms, numbers.Real)
                    or not math.isfinite(exposure_ms) or exposure_ms <= 0):
                raise ValueError('exposure_ms must be finite and positive')
            width = self._driver.get_int('SensorActiveWidth')
            sensor_height = self._driver.get_int('SensorActiveHeight')
            y_start = integer(y_start, 'y_start', 0)
            y_height = integer(sensor_height - y_start if y_height is None else y_height, 'y_height')
            y_binning = integer(y_height if y_binning is None else y_binning, 'y_binning')
            if y_start + y_height > sensor_height or y_height % y_binning:
                raise ValueError('ROI must fit the detector and height must be divisible by y_binning')
            self._configured = False
            self._driver.configure(float(exposure_ms), width, y_start, y_height, y_binning)
            self._settings = (float(exposure_ms), y_start, y_height, y_binning)
            self._configured = True

    def get_spectrum(self, exposure_ms=None, *, y_start=None, y_height=None,
                     y_binning=None, timeout_ms=None):
        """Return a copied uint16 array: (width,) if one row, else (rows, width).

        Without arguments, reuse the last configuration (default: 100 ms,
        full detector height binned to one row). ROI overrides configure anew;
        omitted ROI values then default to full height/full vertical binning.
        An exposure-only override preserves the configured ROI.
        """
        with self._lock:
            self._require_open()
            if not self._configured or any(v is not None for v in (exposure_ms, y_start, y_height, y_binning)):
                exposure = exposure_ms if exposure_ms is not None else (self._settings[0] if self._configured else 100)
                if self._configured and all(v is None for v in (y_start, y_height, y_binning)):
                    _, start, height, binning = self._settings
                else:
                    start, height, binning = (0 if y_start is None else y_start), y_height, y_binning
                self.configure(exposure, start, height, binning)
            timeout = integer(timeout_ms if timeout_ms is not None else math.ceil(self._settings[0]) + 10000, 'timeout_ms')
            if timeout > 2147483647:
                raise ValueError('timeout_ms exceeds the SDK signed 32-bit limit')
            try:
                # Preserve the user's padding fix explicitly.
                frame = self._driver.readNFrames(1, timeout=timeout, framed=1)[0]
            except BaseException:
                self._driver.close(suppress=True)
                self._opened = self._configured = False
                raise
            return frame[0] if frame.shape[0] == 1 else frame
