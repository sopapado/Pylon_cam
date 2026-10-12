"""Run after installing the SDK and simplepicam; requires a real camera."""
import numpy as np
from simplepicam import Camera

with Camera() as cam:
    spectrum = cam.get_spectrum(exposure_ms=100)
    print('Temperature: {:.2f} C'.format(cam.temperature_c))
    print('Detector samples:', spectrum.shape)
    # One detector sample per line, compatible with the old binned .dat files.
    np.savetxt('spectrum.dat', spectrum, fmt='%d')
