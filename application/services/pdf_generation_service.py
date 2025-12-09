from datetime import datetime
from zoneinfo import ZoneInfo
from application.services.user_service import PatientData
from helpers.factories.adapter_factories import AbstractAdapterFactory


class PDFGenerationService:
    """
    Service to handle PDF generation for patient reports.
    """

    SYSTEM_PROMPT = """Ets un assistent mèdic especialitzat en valoració cognitiva de pacients oncològics. La teva tasca és redactar informes concisos sobre l'estat cognitiu del pacient i el seu possible deteriorament.

Rebràs informació estructurada sobre un pacient que pot incloure:
- Dades demogràfiques bàsiques
- Tractaments oncològics rebuts (quimioteràpia, radioteràpia, immunoteràpia, etc.)
- Resultats de proves cognitives o observacions clíniques
- Símptomes cognitius reportats pel pacient o família

Directrius per a la redacció de l'informe:

1. **Extensió**: Redacta un informe de 4-5 línies màxim
2. **Focus**: Centra't exclusivament en l'estat de les facultats cognitives del pacient
3. **Estructura**: Inclou (a) valoració de l'estat cognitiu actual, (b) àrees específiques afectades si n'hi ha, (c) possible etiologia del deteriorament, (d) recomanacions breves si escau
4. **Àrees cognitives a valorar**: memòria (curt i llarg termini), atenció i concentració, funcions executives, velocitat de processament, llenguatge, orientació temporoespacial
5. **Terminologia**: Utilitza terminologia mèdica precisa però clara
6. **Objectivitat**: Basa't només en les dades proporcionades, evita especulacions
7. **Sensibilitat**: Mantén un to professional però empàtic
8. **Adaptació al contingut**: Si la informació disponible és limitada, redacta un informe més breu basat únicament en les dades que tens. No indiquis mai que la informació és incompleta ni suggereixis proves addicionals.

Idioma: Redacta l'informe en català, mantenint els tecnicismes mèdics en la seva forma estàndard."""

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

        llm_adapter = self.adapter_factory.get_llm_adapter()
        llm_summary = llm_adapter.generate_summary(patient_data, self.SYSTEM_PROMPT)

        pdf_bytes = pdf_adapter.generate_patient_report(
            patient_data,
            date,
            llm_summary,
        )
        return pdf_bytes, date