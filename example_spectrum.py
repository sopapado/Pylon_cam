"""Run with 32-bit Python after installing the PICam SDK and connecting the camera."""
import Pylon_init as pyl

try:
    pyl.set_spectrum(exp_time=100, y_start=0, y_height=100, bin=True)
    spectrum = pyl.get_spectrum().reshape(-1)
    print('Number of detector samples:', spectrum.size)  # 1340
    print(spectrum)
finally:
    pyl.close()
