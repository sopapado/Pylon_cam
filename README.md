# Pylon — minimal camera example

The original Pylon scripts and APIs were developed by **Michelangelo Romeo,
engineer at IPCMS/CNRS**, and **Dr Joanna Wolff (RIKEN)**.
The original driver modules also credit **Daniel R. Dietze**.

This first step uses the original driver files directly. There is no Python
package to install and no `simplepicam` API.

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

Python 3.7 is no longer supported; this version matches the existing camera setup.

### Camera drivers and DLLs

If you have installed **LightField supplied by Princeton Instruments**, the
PICam DLL files should already be installed. If you do not have LightField,
get the drivers from the official [PICam SDK & Driver page](https://www.teledynevisionsolutions.com/en-gb/products/picam-sdk-amp-driver/?model=PICAM64).

Check that `DLL_32_bit_path` in `Pylon_init.py` points to your installed
`Picam32.dll`. Close LightField before running the Python script.

### Install NumPy

In this folder, install NumPy using your 32-bit Python:

```powershell
py -3.7-32 -m pip install -r requirements.txt
```

## 2. Configuration and acquisition

```python
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

The module imports use this folder, with no network-drive paths or directory
changes. Plotting, saving files, HyperMap, and package publication are left
for later steps.

Small corrections to the original driver: SDK failures raise errors;
rejected configuration and failed acquisition cannot return a spectrum;
the native `pibln` type is a 32-bit integer, as required by PICam. The original
framed buffer conversion remains in place.

The previous package is saved locally under `archive/previous-simplepicam/`.
Unchanged supplied originals remain under `reference/`. Both directories are
ignored by Git. Nothing has been pushed automatically.

This minimal path has been checked without hardware; acquisition on the
physical camera still needs testing. See [NOTICE.md](NOTICE.md) for the
original licensing notes.
