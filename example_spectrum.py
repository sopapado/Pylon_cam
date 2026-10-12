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
