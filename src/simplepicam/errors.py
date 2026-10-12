"""Exceptions raised by simplepicam."""


class PicamError(RuntimeError):
    """An SDK operation or camera lifecycle operation failed."""


class SDKNotFoundError(PicamError):
    """A compatible installed SDK could not be found or loaded."""


class AcquisitionError(PicamError):
    """Acquisition failed, timed out, or returned incomplete data."""
