from helpers.exceptions.base import ApplicationException


class QRGenerationException(ApplicationException):
    """Excepció personalitzada per errors en la generació de codis QR."""
