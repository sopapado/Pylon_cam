# Pylon - minimal camera example

This Pylon setup is used in the group of **Prof. Stéphane Berciaud at IPCMS, CNRS**.

The original Pylon scripts and APIs were developed by **Dr Michelangelo Romeo,
CNRS Engineer at IPCMS, Strasbourg**, and **Dr Joanna Wolff (RIKEN, Japan)**.
Credit goes also to **Daniel R. Dietze**.

## 1. Prepare the camera computer

### Install Python 3.7, 32-bit

1. Download the official [Python 3.7.9 Windows 32-bit installer](https://www.python.org/ftp/python/3.7.9/python-3.7.9.exe).
   On the [release page](https://www.python.org/downloads/release/python-379/),
   this is called **Windows x86 executable installer**. Choose **x86**, not x86-64.
2. Run the installer and choose **Install Now**. Keep **pip** and the
   **Python launcher (`py`)** enabled if using Customize installation.
   You can keep your other Python installations; the commands below select
   Python 3.7 32-bit explicitly, so changing PATH is unnecessary.
3. Open a new PowerShell window and verify:

```powershell
py -3.7-32 -c "import sys, struct; print(sys.version); print(struct.calcsize('P') * 8, 'bit')"
```

The output should show **3.7.9** and **32 bit**. If `py` is not recognized,
rerun the installer using Modify and enable the Python launcher, then open
a new PowerShell window.

Python 3.7 is no longer supported however this version matches the existing camera code. Fork this project to adapt it to newer Python versions. 

### Camera drivers and DLLs

If you have installed **LightField supplied by Princeton Instruments**, the
PICam DLL files should already be installed. If you do not have LightField,
get the drivers from the official [PICam SDK & Driver page](https://www.teledynevisionsolutions.com/en-gb/products/picam-sdk-amp-driver/?model=PICAM64).

!Check! that `DLL_32_bit_path` in `Pylon_init.py` points to your installed
`Picam32.dll`. Close LightField before running the Python script.

Install the camera drivers appropriate for your Windows version (64-bit
drivers on 64-bit Windows). The **32-bit requirement applies to Python and
the DLL it loads (`Picam32.dll`)**, NOT to the Windows camera drivers.

### Install NumPy

In this folder, install NumPy using your 32-bit Python:

```powershell
py -3.7-32 -m pip install -r requirements.txt
```

## 2. Configuration and acquisition

Replace `C:\path\to\Pylon_cam` with the folder where you downloaded this
repository (the folder containing `Pylon_init.py`). This lets you use the
code from another script or notebook without changing its working folder.

```python
# Configure and acquire a spectrum from a Princeton Instruments Pylon camera.
# Used in Prof. Stéphane Berciaud's group at IPCMS, CNRS.
# Check the installation instructions before running this code:
# https://github.com/sopapado/Pylon_cam#readme
import sys

sys.path.insert(0, r"C:\path\to\Pylon_cam")  # Set your repository folder here
import Pylon_init as pyl

pyl.set_spectrum(exp_time=100, y_start=0, y_height=100, bin=True)
spectrum = pyl.get_spectrum().reshape(-1)
pyl.close()
```

Run the supplied example from this folder:

```powershell
py -3.7-32 example_spectrum.py
```

Importing `Pylon_init` opens the first physical camera, as in the original
workflow. `exp_time` is milliseconds. The example bins all 100 selected rows
into one spectrum. Configure once, then call `get_spectrum()` repeatedly.
Always close when finished; restart the script for a new connection.

`get_spectrum()` keeps the original array shape and uses
`readNFrames(1, framed=1)[0]`. For a binned spectrum, `.reshape(-1)` gives a
one-dimensional array of 1340 samples, excluding the four padding samples.
This first step keeps the original detector width of 1340; general support
for other detectors can be added later.

> **Warning - no wavelength information:** This code returns detector
> intensities by pixel only, without a wavelength axis. Use LightField to
> configure the spectrometer and acquire a reference spectrum, saving its
> wavelength axis for the same grating, central wavelength and detector
> configuration used here. Alternatively, use a calibration lamp with known
> spectral lines to calibrate pixel positions to wavelengths. Update the
> wavelength reference whenever those settings change. Close LightField
> before acquiring with Python. 

## Files

```text
Pylon_init.py             Small setup: open, configure, acquire, close
modules/
    __init__.py
    picamClass.py         Original camera communication/acquisition driver
    picam_types.py        Original PICam constants and ctypes definitions
example_spectrum.py       The example above
requirements.txt         NumPy dependency
```

