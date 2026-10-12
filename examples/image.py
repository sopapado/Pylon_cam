"""Return selected detector rows without vertical binning."""
import numpy as np
from simplepicam import Camera

with Camera() as cam:
    image = cam.get_spectrum(exposure_ms=100, y_start=0, y_height=10, y_binning=1)
    print(image.shape)  # (10, detector_width)
    np.savetxt('image.dat', image, fmt='%d', delimiter='\t')
