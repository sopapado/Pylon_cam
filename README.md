# simplepicam

The original Pylon scripts and APIs were developed by **Michelangelo Romeo,
engineer at IPCMS/CNRS**, and **Dr Joanna Wolff (RIKEN)**.
This package builds on their work. The underlying driver also credits
Daniel R. Dietze; see [NOTICE.md](NOTICE.md) for the retained attribution.

A small Python interface for acquiring spectra with Princeton Instruments
PICam cameras. Adapted from the working Pylon laboratory scripts.

```python
from simplepicam import Camera

with Camera() as cam:
    spectrum = cam.get_spectrum(exposure_ms=100)
    print(spectrum.shape)
    print(cam.temperature_c)
```

The default selects the full detector width and vertically bins the full
detector height into one spectrum. On the original 1340-column detector,
the result has **1340 samples**, not 1344 padded samples. The acquisition
path explicitly preserves `readNFrames(1, framed=1)` and copies only actual
ROI pixels out of the SDK buffer.

Status: initial package, with camera-free regression tests. Real hardware
verification is still required. Nothing has been published to PyPI.
The intended open-source license is GPL-3.0-or-later; review the provenance
questions in [NOTICE.md](NOTICE.md) before public distribution.

## Prerequisites

1. A compatible Princeton Instruments camera and its required connection hardware.
2. The vendor's **PICam SDK/runtime and camera drivers**, installed separately.
   Use the [vendor download page](https://www.teledynevisionsolutions.com/en-gb/products/picam-sdk-amp-driver/?model=PICAM64).
   Confirm your camera works in the vendor software, then close that software
   so it releases the camera. No SDK or proprietary DLL is bundled here.
3. Windows and matching Python/DLL architecture:

| Python process | SDK library |
| --- | --- |
| Python 3.7, **32-bit** (initial target) | `Picam32.dll` |
| A newer **64-bit** Python | `Picam.dll` (64-bit) |

A 64-bit Windows installation can run 32-bit Python and Picam32.dll. The
**Python process**, not Windows bitness, determines which DLL can load.
See the vendor's [PICam manual](https://www.princetoninstruments.com/wp-content/uploads/2022/02/PICAM-5.x-Programmers-Manual-Issue-8-4411-0161-3.pdf).
Use an SDK release that still supplies the architecture your setup requires.
Python 3.7 is end-of-life; it is retained here for the existing laboratory setup.
NumPy 1.21.6 is selected for that interpreter. Newer Python versions use a
compatible newer NumPy resolved by pip.

## Install from this project

In the repository folder, with your desired Python selected:

```powershell
python -m pip install .
```

For the original Python 3.7 32-bit installation, if registered with the launcher:

```powershell
py -3.7-32 -m pip install "pip<24.1"
py -3.7-32 -m pip install .
```

Or install the included wheel using that same interpreter:

```powershell
python -m pip install .\dist\simplepicam-0.1.0-py3-none-any.whl
```

The wheel contains pure Python; camera access remains Windows-only. Importing
the package and running mocked tests does not require Windows or an SDK.
`pip install simplepicam` is the planned future PyPI experience, **not an
installation instruction for this unpublished project**.

## Exposure and vertical ROI

```python
with Camera() as cam:
    # Zero-based rows 5..94, binned in hardware into one detector-width row.
    cam.configure(exposure_ms=100, y_start=5, y_height=90, y_binning=90)
    first = cam.get_spectrum()
    second = cam.get_spectrum()  # reuses the configuration
    third = cam.get_spectrum(exposure_ms=200)  # preserves this ROI

    image = cam.get_spectrum(
        exposure_ms=100, y_start=0, y_height=10, y_binning=1
    )
    # image.shape == (10, detector_width)
```

`y_height=None` means all remaining rows from `y_start`. `y_binning=None`
means bin all selected rows. Explicit binning must divide the height; the
camera must support the requested ROI/binning, which the SDK validates at
commit. Detector dimensions are queried, not hard-coded to 1340 by 100.
Providing any ROI override starts a fresh ROI configuration with these
defaults; an exposure-only override retains the previous ROI.

Output is a detached `numpy.uint16` array: `(width,)` for one output row,
otherwise `(rows, width)`. No software summation, calibration, wavelength
conversion, plotting, or file I/O is performed automatically. The original
wrapper returned floating-point arrays with extra dimensions; this API
normalizes that output. Cast to float before signed differences or arithmetic
that might overflow uint16. Vertical hardware binning may saturate the detector.

```python
import numpy as np
np.savetxt("spectrum.dat", spectrum, fmt="%d")
```

Examples in [examples/](examples/) include single spectra, repeated acquisition,
and unbinned images. Files use one sample per line for a binned spectrum and
tab-separated detector rows for an image. HyperMap was inspected solely as
a usage reference; it has not been copied, modified, or made a dependency.

## DLL discovery

Search order: `Camera(dll_path=...)`, `SIMPLEPICAM_DLL`, `PicamRoot` /
`PICAM_ROOT` (root or Runtime), standard Princeton Instruments PICam Runtime
folders under Windows Program Files/Common Files, then PATH directories.
The PE architecture is checked before loading. No current-folder DLL search
or working-directory changes are required.

For an unusual installation:

```powershell
$env:SIMPLEPICAM_DLL = 'C:\your-installed-sdk\Runtime\Picam32.dll'
```

An explicit bad path fails instead of silently choosing another SDK.
Missing dependencies can still prevent a DLL from loading; repair the vendor
installation rather than copying a single DLL between machines.

## Lifecycle and errors

`Camera()` is inert. Enter its context (recommended), or call `open()` and
eventually `close()`. It opens the first physical camera. This initial API
supports one active session per process, one ROI, monochrome 16-bit pixels,
and one frame per readout. Kinetics/multi-frame modes are rejected. Multiple
cameras and asynchronous acquisition are outside this release's scope.

Exposure is in milliseconds. Default timeout is exposure plus 10 seconds;
use `get_spectrum(timeout_ms=60000)` for slow readout or external triggering.
Existing trigger settings are preserved; an externally triggered camera will
need its trigger. Calls on one Camera are serialized, and close waits for a
blocking acquisition to finish or time out.

`SDKNotFoundError`, `AcquisitionError`, and their base `PicamError` identify
SDK, acquisition, and configuration failures. Input validation raises
`ValueError`. Acquisition failures close the session. Failed configuration
is not used for acquisition. Cleanup attempts stop, close, and uninitialize
even when an earlier step fails. Cleanup failures are reported (or warned
without hiding an exception already in progress) and require restarting the
process. No automatic demo data or silent partial spectra are returned.

## Development and release

### Project structure and original source files

The name `simplepicam` follows the proposed `from simplepicam import Camera`
API in the original project request. It names this Python package, not the
vendor SDK or the original Pylon scripts.

| Package file | Purpose and original source |
| --- | --- |
| `src/simplepicam/camera.py` | Simple public `Camera` API; adapts the configuration and spectrum workflow from `Pylon_init.py`. |
| `src/simplepicam/_driver.py` | Focused adaptation of `picamClass.py`: SDK communication, ROI configuration, commit, synchronous acquisition, and cleanup. Retains the `readNFrames(1, framed=1)` path. |
| `src/simplepicam/_types.py` | Copied from `picam_types.py`, retaining its definitions and attribution, with the native boolean and byte type corrections described in the inspection notes. |
| `src/simplepicam/discovery.py` | New code that locates and loads the installed SDK DLL. |
| `src/simplepicam/errors.py` | New exception classes for reporting failures. |
| `src/simplepicam/__init__.py` | Exports `Camera` and the exceptions for convenient imports. |

The original three files remain unchanged in the local ignored `reference/`
folder. That folder is not uploaded to GitHub or included in releases.
The package imports the adapted files under `src/simplepicam/`; it does not
import or execute the old scripts. HyperMap was only a usage reference, and
`Picam32.dll` must come from the separately installed vendor SDK.

`examples/` contains acquisition scripts, `tests/` contains camera-free tests,
and `docs/` contains inspection, validation, and release notes.

### Build and test

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip install -r requirements-dev.txt
python -m build
python -m twine check dist/*.whl dist/*.tar.gz
python tools/make_release_zip.py
```

Tests use a fake SDK through the actual driver and ctypes structures. They
cover padding, detached buffers, ROI orientation, repeated acquisition,
errors, cleanup, discovery, and architecture mismatch. A GitHub Actions
workflow is included for Windows Python 3.7 x86, 3.11 x64, and 3.13 x64.
Configured CI coverage is not evidence of a completed hardware test.

See [inspection notes](docs/INSPECTION.md), [validation results](docs/VALIDATION.md),
and the [release checklist](docs/RELEASE.md). This folder is ready for review
in GitHub; publication requires explicit owner approval and resolution of
the documented licensing questions.
