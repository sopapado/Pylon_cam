"""Minimal setup based on the original Pylon_init.py.

Original Pylon scripts: Michelangelo Romeo (IPCMS/CNRS) and
Dr Joanna Wolff (RIKEN). Original Pylon_init update: 20 September 2022.
The driver modules retain their original author and upstream credits.

Importing this module opens the camera, as in the original script.
"""
import ctypes
import os
from pathlib import Path

# Edit this one line if the installed SDK is somewhere else.
DLL_32_bit_path = r"C:\Program Files\Common Files\Princeton Instruments\Picam\Runtime\Picam32.dll"

if os.name != 'nt' or ctypes.sizeof(ctypes.c_void_p) != 4:
    raise RuntimeError('This initial Pylon setup requires Windows and 32-bit Python.')
if not Path(DLL_32_bit_path).is_file():
    raise FileNotFoundError(
        'PICam32.dll was not found. Install the Princeton Instruments PICam SDK '
        'and drivers, or correct DLL_32_bit_path in Pylon_init.py.'
    )

from modules.picamClass import picam

cam = picam()
_configured = False


def set_spectrum(exp_time, y_start, y_height, bin=True):
    """Exposure in ms; select detector rows, optionally binning them together."""
    global _configured
    if cam is None:
        raise RuntimeError('Camera is closed. Restart your script to reconnect.')
    _configured = False
    cam.setParameter('ExposureTime', exp_time)
    cam.setROI(0, 1340, 1, y_start, y_height, y_height if bin else 1)
    cam.sendConfiguration()
    _configured = True


def get_spectrum():
    """Acquire using the original framed=1 fix (no 1344-sample padding).

    Keeps the original array shape. For a binned spectrum use .reshape(-1)
    to get a simple array of 1340 values.
    """
    if cam is None or not _configured:
        raise RuntimeError('Call set_spectrum before get_spectrum.')
    return cam.readNFrames(1, framed=1)[0]


def close():
    """Release the camera and SDK when finished."""
    global cam, _configured
    if cam is not None:
        try:
            cam.uninitLibrary()
        finally:
            cam = None
            _configured = False


cam.loadLibrary(DLL_32_bit_path)
if not hasattr(cam, 'lib'):
    raise RuntimeError('Could not load PICam32.dll. Check the vendor SDK installation.')
cam.initLibrary()
try:
    cam.connect()  # First physical camera; no automatic demo-camera fallback.
except Exception:
    try:
        close()
    except Exception:
        pass  # Preserve the original connection error.
    raise
