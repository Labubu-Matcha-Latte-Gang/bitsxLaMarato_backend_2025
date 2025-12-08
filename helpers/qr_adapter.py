from abc import ABC, abstractmethod
from typing import Literal
import qrcode
import qrcode.image.svg
import io

from helpers.debugger.logger import AbstractLogger

logger = AbstractLogger.get_instance()

class AbstractQRAdapter(ABC):
    """Abstract adapter for generating QR codes."""

    def _normalize_color(self, color: str) -> str:
        """Normalize color strings to hex format.

        Args:
            color (str): Color string (e.g., '#FFFFFF', '#000000').

        Returns:
            str: Normalized hex color string.
        """
        color = color.strip()
        if not color.startswith("#"):
            return f"#{color}"
        return color

    @abstractmethod
    def generate_qr(self, data: bytes | str, format: Literal['png', 'svg'] = 'svg', fill_color: str = '#000000', back_color: str = '#FFFFFF', box_size: int = 10, border: int = 4) -> tuple[io.BytesIO, str]:
        """
        Generate a QR code based on the provided data.

        Args:
            data (bytes | str): Data to encode in the QR code.
            format (Literal['png', 'svg']): Format of the QR code image. Default is 'svg'.
            fill_color (str): Color of the QR code. Default is black.
            back_color (str): Background color of the QR code. Default is white.
            box_size (int): Size of each box in the QR code. Default is 10.
            border (int): Border size around the QR code. Default is 4.
        Returns:
            tuple[io.BytesIO, str]: A tuple containing the QR code image as a BytesIO stream and the content type.
        """
        raise NotImplementedError
    
class QRAdapter(AbstractQRAdapter):
    """Concrete adapter for generating QR codes."""

    def generate_qr(self, data: bytes | str, format: Literal['png', 'svg'] = 'svg', fill_color: str = '#000000', back_color: str = '#FFFFFF', box_size: int = 10, border: int = 4) -> tuple[io.BytesIO, str]:
        logger.info("Generating QR code", module="QRAdapter", metadata={"format": format, "fill_color": fill_color, "back_color": back_color, "box_size": box_size, "border": border})
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=box_size,
                border=border,
            )
            qr.add_data(data)
            qr.make(fit=True)

            stream = io.BytesIO()

            fill_color = self._normalize_color(fill_color)
            back_color = self._normalize_color(back_color)

            if format.lower() == 'svg':
                factory = qrcode.image.svg.SvgPathImage
                img = qr.make_image(image_factory=factory, fill_color=fill_color, back_color=back_color)
                img.save(stream)
                stream.seek(0)
                return stream, "image/svg+xml"
            
            else: # PNG
                img = qr.make_image(fill_color=fill_color, back_color=back_color)
                img.save(stream, format="PNG")
                stream.seek(0)
                return stream, "image/png"
        except Exception as e:
            logger.error("Error generating QR code", module="QRAdapter", error=e)
            raise e