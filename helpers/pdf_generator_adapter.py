from __future__ import annotations
from abc import ABC, abstractmethod
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from typing import TYPE_CHECKING
from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.pdf_exceptions import PDFGenerationException, ReportDataTransformationException

if TYPE_CHECKING:
    from application.services.user_service import PatientData

class AbstractPDFGeneratorAdapter(ABC):
    """Abstract adapter for generating PDF documents."""

    logger = AbstractLogger.get_instance()

    @staticmethod
    def _transform_patient_data(patient_data: PatientData) -> dict:
        """Transform patient data into a serializable dictionary.

        Args:
            patient_data (PatientData): The patient data to transform.

        Returns:
            dict: The transformed patient data.
        """
        try:
            match patient_data['patient']['role']['gender']:
                case 'male':
                    patient_data['patient']['role']['gender'] = 'Home'
                case 'female':
                    patient_data['patient']['role']['gender'] = 'Dona'
                case _:
                    patient_data['patient']['role']['gender'] = 'Altres'

            return patient_data
        except KeyError as e:
            raise ReportDataTransformationException("Error al transformar les dades del pacient.") from e
        except Exception as e:
            raise ReportDataTransformationException("Error inesperat al transformar les dades del pacient.") from e

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

            transformed_data = self._transform_patient_data(patient_data)
            self.logger.debug("Transformed patient data for PDF generation", module="PDFGeneratorAdapter", metadata={"transformed_data": transformed_data})

            html_out = template.render(
                data=transformed_data,
                data_informe=date
            )

            pdf_bytes = HTML(string=html_out).write_pdf()
        except ReportDataTransformationException as e:
            self.logger.error("Error transforming patient data for PDF generation", module="PDFGeneratorAdapter", error=e)
            raise e
        except Exception as e:
            self.logger.error("Error generating PDF report", module="PDFGeneratorAdapter", error=e)
            raise PDFGenerationException("Error al generar el PDF.") from e

        if not pdf_bytes:
            self.logger.error("Generated PDF is empty", module="PDFGeneratorAdapter")
            raise PDFGenerationException("Ha ocurregut un error en generar el PDF.")
        
        return pdf_bytes
