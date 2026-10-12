"""Focused adaptation of picamClass.py's synchronous acquisition path.

Original work: Daniel R. Dietze; modifications: Michelangelo Romeo (2020).
Further adapted for simplepicam (2026). GPL-3.0-or-later; see NOTICE.md.
"""
import ctypes as c
import threading
import warnings

import numpy as np

from . import _types as t
from .discovery import load_dll
from .errors import AcquisitionError, PicamError


def bind(lib):
    """Declare every native function used here, including pointer arguments."""
    p = c.POINTER
    signatures = {
        'IsLibraryInitialized': [p(t.pibln)], 'InitializeLibrary': [],
        'UninitializeLibrary': [], 'OpenFirstCamera': [p(t.pivoid)],
        'CloseCamera': [t.pivoid], 'StopAcquisition': [t.pivoid],
        'IsAcquisitionRunning': [t.pivoid, p(t.pibln)],
        'GetParameterIntegerValue': [t.pivoid, t.piint, p(t.piint)],
        'GetParameterFloatingPointValue': [t.pivoid, t.piint, p(t.piflt)],
        'ReadParameterFloatingPointValue': [t.pivoid, t.piint, p(t.piflt)],
        'CanReadParameter': [t.pivoid, t.piint, p(t.pibln)],
        'SetParameterFloatingPointValue': [t.pivoid, t.piint, t.piflt],
        'SetParameterRoisValue': [t.pivoid, t.piint, p(t.PicamRois)],
        'GetParameterRoisValue': [t.pivoid, t.piint, p(p(t.PicamRois))],
        'DestroyRois': [p(t.PicamRois)],
        'CommitParameters': [t.pivoid, p(p(t.piint)), p(t.piint)],
        'DestroyParameters': [p(t.piint)],
        'Acquire': [t.pivoid, t.pi64s, t.piint, p(t.PicamAvailableData), p(t.piint)],
    }
    for name, args in signatures.items():
        fn = getattr(lib, 'Picam_' + name)
        fn.argtypes = args
        fn.restype = t.piint


def unpack_frame(address, readouts, readout_stride, frame_stride, frames, width, height):
    """Preserve framed=1 trimming; never expose an SDK-owned buffer to callers."""
    pixels = width * height
    if (not address or readouts < 1 or min(width, height, frames) < 1
            or frame_stride < pixels * 2 or frame_stride % 2
            or readout_stride < frame_stride * frames or readout_stride % 2):
        raise AcquisitionError('Invalid or incomplete PICam frame layout')
    # One requested frame: copy its actual pixels, excluding stride padding.
    native = c.cast(address, c.POINTER(t.pi16u * pixels)).contents
    return np.frombuffer(native, dtype=np.uint16).copy().reshape(height, width)


class Driver:
    # The SDK is process-global. Limit this deliberately small API to one session.
    _lock = threading.Lock()
    _active = False

    def __init__(self, dll_path=None):
        self.dll_path = dll_path
        self.lib = None
        self.cam = t.pivoid()
        self.owned_library = False
        self.reserved = False
        self.shape = None

    def call(self, name, *args):
        code = getattr(self.lib, 'Picam_' + name)(*args)
        if code:
            raise PicamError('{} failed: {} ({})'.format(name, t.PicamErrorLookup.get(code, 'UnknownError'), code))

    def open(self):
        with Driver._lock:
            if Driver._active:
                raise PicamError('Only one simplepicam camera session may be open per process')
            Driver._active = self.reserved = True
        try:
            self.lib = load_dll(self.dll_path)
            bind(self.lib)
            initialized = t.pibln()
            self.call('IsLibraryInitialized', c.byref(initialized))
            if initialized.value:
                raise PicamError('PICam is already initialized by another client; close that client first')
            self.call('InitializeLibrary')
            self.owned_library = True
            self.call('OpenFirstCamera', c.byref(self.cam))
        except BaseException:
            self.close(suppress=True)
            raise

    def close(self, suppress=False):
        failures = []
        if self.lib is not None and self.cam.value:
            for name in ('StopAcquisition', 'CloseCamera'):
                try:
                    if name == 'StopAcquisition':
                        running = t.pibln()
                        self.call('IsAcquisitionRunning', self.cam, c.byref(running))
                        if not running.value:
                            continue
                    self.call(name, self.cam)
                except Exception as exc:
                    failures.append(str(exc))
            self.cam = t.pivoid()
        if self.owned_library:
            try:
                self.call('UninitializeLibrary')
            except Exception as exc:
                failures.append(str(exc))
            self.owned_library = False
        if self.reserved:
            with Driver._lock:
                # Failed native cleanup leaves SDK state uncertain. Require a
                # process restart rather than risk opening another session.
                Driver._active = bool(failures)
            self.reserved = False
        if failures:
            message = 'PICam cleanup failed; restart this process: ' + '; '.join(failures)
            if suppress:
                warnings.warn(message, RuntimeWarning)
            else:
                raise PicamError(message)

    def get_int(self, name):
        value = t.piint()
        self.call('GetParameterIntegerValue', self.cam, t.PicamParameter[name], c.byref(value))
        return value.value

    def temperature(self):
        param = t.PicamParameter['SensorTemperatureReading']
        readable = t.pibln()
        self.call('CanReadParameter', self.cam, param, c.byref(readable))
        value = t.piflt()
        name = 'ReadParameterFloatingPointValue' if readable.value else 'GetParameterFloatingPointValue'
        self.call(name, self.cam, param, c.byref(value))
        return value.value

    def configure(self, exposure, width, y, height, binning):
        self.shape = None
        self.call('SetParameterFloatingPointValue', self.cam, t.PicamParameter['ExposureTime'], exposure)
        roi = t.PicamRoi(0, width, 1, y, height, binning)
        rois = t.PicamRois(c.pointer(roi), 1)
        self.call('SetParameterRoisValue', self.cam, t.PicamParameter['Rois'], c.byref(rois))
        failed = c.POINTER(t.piint)()
        count = t.piint()
        try:
            self.call('CommitParameters', self.cam, c.byref(failed), c.byref(count))
            if count.value:
                names = [t.PicamParameterLookup.get(failed[i], str(failed[i])) for i in range(count.value)]
                raise PicamError('Camera rejected parameters: ' + ', '.join(names))
        finally:
            if failed:
                self.call('DestroyParameters', failed)
        actual = c.POINTER(t.PicamRois)()
        try:
            self.call('GetParameterRoisValue', self.cam, t.PicamParameter['Rois'], c.byref(actual))
            if not actual or actual.contents.roi_count != 1:
                raise PicamError('Expected exactly one committed ROI')
            r = actual.contents.roi_array[0]
            if tuple(getattr(r, key) for key in ('x', 'width', 'x_binning', 'y', 'height', 'y_binning')) != (0, width, 1, y, height, binning):
                raise PicamError('Committed ROI differs from requested ROI')
            self.shape = (height // binning, width)
        finally:
            if actual:
                self.call('DestroyRois', actual)

    def readNFrames(self, N=1, timeout=10000, framed=1):
        """Internal compatibility path: the original readNFrames(1, framed=1)."""
        if N != 1 or framed != 1 or self.shape is None:
            raise AcquisitionError('Only one configured, framed acquisition is supported')
        if self.get_int('PixelFormat') != t.PicamPixelFormat['Monochrome16Bit']:
            raise AcquisitionError('Only monochrome 16-bit pixels are supported')
        running = t.pibln()
        self.call('IsAcquisitionRunning', self.cam, c.byref(running))
        if running.value:
            raise AcquisitionError('An acquisition is already running')
        stride = self.get_int('ReadoutStride')
        frame_stride = self.get_int('FrameStride')
        frames = self.get_int('FramesPerReadout')
        if frames != 1:
            raise AcquisitionError('This API requires one frame per readout; disable kinetics/multi-frame modes')
        data, errors = t.PicamAvailableData(), t.piint()
        try:
            self.call('Acquire', self.cam, N, timeout, c.byref(data), c.byref(errors))
        except PicamError as exc:
            raise AcquisitionError(str(exc)) from exc
        if errors.value:
            raise AcquisitionError('PICam acquisition error mask: 0x{:x} (1=data lost, 2=connection lost)'.format(errors.value))
        height, width = self.shape
        return [unpack_frame(data.initial_readout, data.readout_count, stride, frame_stride, frames, width, height)]
