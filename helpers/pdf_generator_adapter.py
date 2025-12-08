from abc import ABC, abstractmethod
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from application.services.user_service import PatientData
from helpers.exceptions.pdf_exceptions import PDFGenerationException

class AbstractPDFGeneratorAdapter(ABC):
    """Abstract adapter for generating PDF documents."""
    
    @abstractmethod
    def generate_patient_report(self, patient_data: PatientData, date: str, template_path: str = 'templates/patient_report.html') -> bytes:
        """
        Generate a PDF report for a patient.
        Args:
            patient_data (PatientData): Data of the patient to include in the report.
            date (str): Date for the report.
            template_path (str): Path to the HTML template for the report.
        Returns:
            bytes: The generated PDF document as a byte stream.
        Raises:
            PDFGenerationException: If there is an error during PDF generation.
        """
        raise NotImplementedError
    
class PDFGeneratorAdapter(AbstractPDFGeneratorAdapter):
    """Concrete adapter for generating PDF documents."""

    __env = Environment(loader=FileSystemLoader('.'))
    
    def generate_patient_report(self, patient_data: PatientData, date: str, template_path: str = 'templates/patient_report.html') -> bytes:
        try:
            template = self.__env.get_template(template_path)

            html_out = template.render(
                data=patient_data,
                data_informe=date
            )

            pdf_bytes = HTML(string=html_out).write_pdf()
        except Exception as e:
            raise PDFGenerationException("Error al generar el PDF.") from e

        if not pdf_bytes:
            raise PDFGenerationException("Ha ocurregut un error en generar el PDF.")
        
        return pdf_bytes
