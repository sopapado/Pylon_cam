"""Configure once, acquire repeatedly, as in the original mapping workflow."""
import numpy as np
from simplepicam import Camera

with Camera() as cam:
    cam.configure(exposure_ms=100, y_start=5, y_height=90, y_binning=90)
    for index in range(3):
        spectrum = cam.get_spectrum()
        np.savetxt('spectrum_{:03d}.dat'.format(index), spectrum, fmt='%d')
