# Source inspection and design decisions

Inspected the three supplied source files on 12 October 2026. Local unmodified
copies are retained in ignored reference/ for comparison. Read the relevant
HyperMap setup, set_spectrum/get_spectrum and output-call sections only;
HyperMap and the vendor DLL are not incorporated in the package.

## Dependencies

- picamClass.py: ctypes, os and NumPy; picam_types.py: ctypes.
- Pylon_init.py: NumPy and matplotlib, hard-coded DLL and module directories,
  changes to the working directory, and camera initialization at import time.
- The new runtime needs only NumPy plus the Python standard library and
  an independently installed vendor SDK. No matplotlib, Cython, GUI, motion
  stage, SPE reader, or HyperMap dependency.

## Preserved workflow

Set ExposureTime in ms, set full-width ROI and vertical binning, commit,
query the committed ROI, then acquire synchronously with Picam_Acquire.
The original get_spectrum calls readNFrames(1, framed=1)[0]; the new public
method retains that explicit internal call. ReadoutStride and FrameStride
include padding; only the ROI pixel count is returned. The original
1344-word readout / 1340-pixel spectrum has a regression test.

The broad legacy driver was reduced to this supported path instead of
shipping untested asynchronous/demo/configuration features. _types.py keeps
the original enums and structures with attribution. _driver.py adapts the
original synchronous sequence and buffer-trimming logic with checked errors.

## Corrections and deliberate API differences

- Explicit argtypes/restype protect native handles and 64-bit pointers.
- pibln is c_int, not c_bool; pibyte is unsigned. Verified against the vendor
  pil_platform.h available in the areaDetector SDK header mirror:
  https://github.com/areaDetector/ADPICam/blob/master/PICamSupport/pil_platform.h
  That header also specifies stdcall on Windows, retained via WinDLL.
- No connection at import time, demo-camera fallback, global cam, chdir,
  wildcard imports, or plotting. The first camera is opened directly.
- Failed commits and acquisition status masks raise exceptions rather than
  only appending log messages. SDK-owned ROI and failed-parameter allocations
  are released promptly, and acquisition arrays are copied before returning.
- The old framed single-ROI shape was (frames, width, height). The public
  output now uses conventional (rows, width), or a 1-D binned spectrum.
- Data remains native uint16 rather than being converted to float. Call
  astype(float) when appropriate for subsequent numerical processing.
- Default vertical ROI is the full detected sensor height, fully binned;
  unsupported hardware binning is reported by the SDK, not emulated silently.
- Explicit SDK ownership and a one-session policy prevent this package from
  uninitializing an SDK owned by another in-process client.

## Licensing

Both low-level source files declare GPL without a version; Dietze's stated
upstream is GPL-3.0-or-later. Pylon_init.py names Joanna Wolff but contains no
explicit grant. NOTICE.md records attribution and the outstanding permission
review. SDK redistribution rights were not established, so no DLL is copied
into the source distribution or ZIP. LICENSE covers intended open-source
release terms, not vendor software or unconfirmed third-party permissions.
