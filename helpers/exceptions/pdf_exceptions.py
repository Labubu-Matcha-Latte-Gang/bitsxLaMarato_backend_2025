class PDFGenerationException(Exception):
    """Excepció personalitzada per errors en la generació de PDFs."""
    pass

class InvalidZoneInfoException(PDFGenerationException):
    """Excepció personalitzada per errors en la zona horària."""
    pass