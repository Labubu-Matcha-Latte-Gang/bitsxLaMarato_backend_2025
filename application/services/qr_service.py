from dataclasses import dataclass
import io
from typing import Literal
from helpers.factories.adapter_factories import AbstractAdapterFactory

@dataclass
class QRPayload:
    data: bytes | str
    format: Literal['png', 'svg'] = 'svg'
    fill_color: str = '#000000'
    back_color: str = '#FFFFFF'
    box_size: int = 10
    border: int = 4

    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "format": self.format,
            "fill_color": self.fill_color,
            "back_color": self.back_color,
            "box_size": self.box_size,
            "border": self.border,
        }

class QRService:
    """
    Service to handle QR code generation.
    """

    def __init__(self, adapter_factory: AbstractAdapterFactory | None = None) -> None:
        self.adapter_factory = adapter_factory or AbstractAdapterFactory.get_instance()

    def generate_qr_code(self, data: QRPayload) -> tuple[io.BytesIO, str]:
        """
        Generate a QR code based on the provided data.
        Args:
            data (QRPayload): The payload containing QR code generation parameters.
        Returns:
            tuple[io.BytesIO, str]: A tuple containing the QR code image as a BytesIO stream and the content type.
        """
        
        qr_adapter = self.adapter_factory.get_qr_adapter()
        qr = qr_adapter.generate_qr(**data.to_dict())
        return qr