"""Simple synchronous spectra from Princeton Instruments PICam cameras."""
from .camera import Camera
from .errors import AcquisitionError, PicamError, SDKNotFoundError

__version__ = '0.1.0'
__all__ = ['Camera', 'PicamError', 'SDKNotFoundError', 'AcquisitionError']
