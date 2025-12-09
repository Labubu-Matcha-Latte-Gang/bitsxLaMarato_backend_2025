from datetime import datetime
from zoneinfo import ZoneInfo
from application.services.user_service import PatientData
from helpers.factories.adapter_factories import AbstractAdapterFactory


class PDFGenerationService:
    """
    Service to handle PDF generation for patient reports.
    """

    def __init__(self, adapter_factory: AbstractAdapterFactory | None = None) -> None:
        self.adapter_factory = adapter_factory or AbstractAdapterFactory.get_instance()

    def generate_patient_report(self, patient_data: PatientData, timezone_wanted: ZoneInfo) -> tuple[bytes, str]:
        """
        Generate a PDF report for the specified patient.
        Args:
            patient_data (PatientData): Data of the patient to include in the report.
            timezone_wanted (ZoneInfo): Timezone for date formatting.
        Returns:
            tuple[bytes, str]: The generated PDF document as a byte stream and the formatted date.
        """

        pdf_adapter = self.adapter_factory.get_pdf_generator_adapter()

        date = datetime.now(timezone_wanted).strftime("%d/%m/%Y")
        pdf_bytes = pdf_adapter.generate_patient_report(
            patient_data,
            date
        )
        return pdf_bytes, date