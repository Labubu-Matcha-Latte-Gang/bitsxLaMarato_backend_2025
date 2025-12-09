from abc import ABC, abstractmethod

from helpers.graphic_adapter import AbstractGraphicAdapter, SimplePlotlyAdapter
from helpers.llm_adapter import AbstractLlmAdapter, GeminiAdapter
from helpers.pdf_generator_adapter import AbstractPDFGeneratorAdapter, PDFGeneratorAdapter
from helpers.qr_adapter import AbstractQRAdapter, QRAdapter


class AbstractAdapterFactory(ABC):
    """Abstract factory for creating adapter instances."""
    __instance: 'AbstractAdapterFactory' = None

    @classmethod
    def get_instance(cls) -> 'AbstractAdapterFactory':
        """Return the singleton instance of the adapter factory."""
        if cls.__instance is None:
            cls.__instance = AdapterFactory()
        return cls.__instance

    @abstractmethod
    def get_graphic_adapter(self) -> AbstractGraphicAdapter:
        """Return an instance of a graphic adapter."""
        raise NotImplementedError
    
    @abstractmethod
    def get_qr_adapter(self) -> AbstractQRAdapter:
        """Return an instance of a QR code adapter."""
        raise NotImplementedError
    
    @abstractmethod
    def get_pdf_generator_adapter(self) -> AbstractPDFGeneratorAdapter:
        """Return an instance of a PDF generator adapter."""
        raise NotImplementedError
    
    @abstractmethod
    def get_llm_adapter(self) -> AbstractLlmAdapter:
        """Return an instance of a LLM adapter."""
        raise NotImplementedError
    
class AdapterFactory(AbstractAdapterFactory):
    """Concrete factory for creating adapter instances."""

    def get_graphic_adapter(self) -> SimplePlotlyAdapter:
        return SimplePlotlyAdapter()
    
    def get_qr_adapter(self) -> QRAdapter:
        return QRAdapter()
    
    def get_pdf_generator_adapter(self) -> PDFGeneratorAdapter:
        return PDFGeneratorAdapter()
    
    def get_llm_adapter(self) -> GeminiAdapter:
        return GeminiAdapter()