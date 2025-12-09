from abc import ABC, abstractmethod
from typing import Literal
import qrcode
import qrcode.image.svg
import io
import base64
import mimetypes
import xml.etree.ElementTree as ET
from PIL import Image

from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.qr_exceptions import QRGenerationException

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
    def generate_qr(self, data: bytes | str, format: Literal['png', 'svg'] = 'svg', fill_color: str = '#000000', back_color: str = '#FFFFFF', box_size: int = 10, border: int = 4, logo_path: str = 'static/labubu-logo.png') -> tuple[io.BytesIO, str]:
        """
        Generate a QR code based on the provided data.

        Args:
            data (bytes | str): Data to encode in the QR code.
            format (Literal['png', 'svg']): Format of the QR code image. Default is 'svg'.
            fill_color (str): Color of the QR code. Default is black.
            back_color (str): Background color of the QR code. Default is white.
            box_size (int): Size of each box in the QR code. Default is 10.
            border (int): Border size around the QR code. Default is 4.
            logo_path (str): Path to the logo image to embed in the QR code. Default is 'static/labubu-logo.png'.
        Returns:
            tuple[io.BytesIO, str]: A tuple containing the QR code image as a BytesIO stream and the content type.
        """
        raise NotImplementedError
    
class QRAdapter(AbstractQRAdapter):
    """Concrete adapter for generating QR codes."""

    def __get_logo_base64(self, logo_path: str) -> str:
        """Read the local file and convert it to a base64 string with its mime type."""
        mime_type, _ = mimetypes.guess_type(logo_path)
        if not mime_type:
            mime_type = "image/png"
            
        with open(logo_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        return f"data:{mime_type};base64,{encoded_string}"

    def __embed_logo_in_svg(self, svg_data: bytes, logo_path: str, back_color: str) -> bytes:
        """Manipulate the SVG XML to inject the <image> tag."""
        try:
            # Register SVG namespace so ElementTree doesn't add 'ns0:' prefix to tags
            ET.register_namespace('', "http://www.w3.org/2000/svg")
            
            tree = ET.ElementTree(ET.fromstring(svg_data))
            root = tree.getroot()
            
            logo_b64 = self.__get_logo_base64(logo_path)

            pos_x = "38%"
            pos_y = "38%"
            width = "24%"
            height = "24%"

            bg_rect = ET.Element("rect", {
                "x": pos_x,
                "y": pos_y,
                "width": width,
                "height": height,
                "fill": back_color
            })
            root.append(bg_rect)
            
            image_element = ET.Element("image", {
                "href": logo_b64,
                "x": pos_x,
                "y": pos_y,
                "width": width,
                "height": height,
                "preserveAspectRatio": "xMidYMid meet"
            })
            root.append(image_element)
            
            out_stream = io.BytesIO()
            tree.write(out_stream, encoding='utf-8', xml_declaration=True)
            out_stream.seek(0)
            return out_stream.read()
            
        except Exception as e:
            logger.error(f"Error embedding logo in SVG: {e}", module="QRAdapter")
            return svg_data  # If it fails, return the original SVG without the logo

    def generate_qr(self, data: bytes | str, format: Literal['png', 'svg'] = 'svg', fill_color: str = '#000000', back_color: str = '#FFFFFF', box_size: int = 10, border: int = 4, logo_path: str = 'static/labubu-logo.png') -> tuple[io.BytesIO, str]:
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

                temp_stream = io.BytesIO()
                img.save(temp_stream)
                svg_bytes = temp_stream.getvalue()

                if logo_path:
                    svg_bytes = self.__embed_logo_in_svg(svg_bytes, logo_path, back_color)

                stream.write(svg_bytes)
                stream.seek(0)
                return stream, "image/svg+xml"
            
            else: # PNG
                img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGBA")
                if logo_path:
                    try:
                        logo = Image.open(logo_path)
                        qr_width = img.size[0]
                        logo_max_size = qr_width // 4  
                        logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)

                        logo_pos = ((img.size[0] - logo.size[0]) // 2, (img.size[1] - logo.size[1]) // 2)
                        logo_bg = Image.new("RGBA", logo.size, back_color)
                        img.paste(logo_bg, logo_pos)
                        
                        mask = logo if logo.mode == 'RGBA' else None
                        img.paste(logo, logo_pos, mask)
                    except Exception as e:
                        logger.error(f"Could not process logo: {e}", module="QRAdapter")

                img.save(stream, format="PNG")
                stream.seek(0)
                return stream, "image/png"
        except Exception as e:
            logger.error("Error generating QR code", module="QRAdapter", error=e)
            raise QRGenerationException("Error al generar el codi QR.") from e