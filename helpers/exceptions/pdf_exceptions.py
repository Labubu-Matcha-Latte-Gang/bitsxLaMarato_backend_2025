class PDFGenerationException(Exception):
    """Excepció personalitzada per errors en la generació de PDFs."""
    pass

class InvalidZoneInfoException(PDFGenerationException):
    """Excepció personalitzada per errors en la zona horària."""
    pass

class ReportDataTransformationException(PDFGenerationException):
    """Excepció personalitzada per errors en la transformació de dades de l'informe."""
    pass