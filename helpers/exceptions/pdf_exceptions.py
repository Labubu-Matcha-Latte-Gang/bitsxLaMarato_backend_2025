from helpers.exceptions.base import ApplicationException


class PDFGenerationException(ApplicationException):
    """Excepció personalitzada per errors en la generació de PDFs."""


class InvalidZoneInfoException(PDFGenerationException):
    """Excepció personalitzada per errors en la zona horària."""


class ReportDataTransformationException(PDFGenerationException):
    """Excepció personalitzada per errors en la transformació de dades de l'informe."""
