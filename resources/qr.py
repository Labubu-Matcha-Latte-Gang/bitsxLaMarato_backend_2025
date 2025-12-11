from datetime import datetime, timedelta
from flask import send_file, g, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import IntegrityError
from zoneinfo import ZoneInfo

from application.services.qr_service import QRPayload
from db import db
from helpers.debugger.logger import AbstractLogger
from helpers.decorators import roles_required
from helpers.enums.user_role import UserRole
from helpers.exceptions.pdf_exceptions import InvalidZoneInfoException, PDFGenerationException
from helpers.exceptions.qr_exceptions import QRGenerationException
from helpers.exceptions.integrity_exceptions import DataIntegrityException
from application.container import ServiceFactory
from helpers.exceptions.user_exceptions import UserNotFoundException
from urllib.parse import urlencode
from schemas import (
    QRGenerateSchema,
)
from domain.entities.user import Doctor, Patient

blp = Blueprint('qr', __name__, description="Generació de codi QR per obtenir informes de pacients.")


@blp.route('')
class QRResource(MethodView):
    """
    Endpoints per obtenir codis QR.
    """

    logger = AbstractLogger.get_instance()

    @roles_required([UserRole.PATIENT, UserRole.DOCTOR])
    @blp.arguments(QRGenerateSchema, location='json')
    @blp.doc(
        summary="Obtenir un codi QR per a l'informe mèdic.",
        description="Genera un codi QR que permet obtenir l'informe mèdic d'un pacient.",
    )
    @blp.response(200, description="Codi QR generat correctament.", content_type=["image/png", "image/svg+xml"])
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="No tens permís per generar aquest codi QR.")
    @blp.response(422, description="El cos de la sol·licitud no ha superat la validació.")
    @blp.response(500, description="Error inesperat del servidor en generar el codi QR.")
    def post(self, data: dict):
        """
        Obté un codi QR per a l'informe mèdic del pacient.
        Es pot generar tant en format PNG com SVG, però es recomana SVG per la seva flexibilitat a l'hora d'aplicar-li estils.
        Compte! Si el `fill_color` i el `back_color` s'assemblen massa, el codi QR podria no ser llegible.
        """
        try:
            service_factory = ServiceFactory.get_instance()
            qr_service = service_factory.build_qr_service()
            user_service = service_factory.build_user_service()
            patient_service = service_factory.build_patient_service()

            requester = g.current_user
            target_email = data.get("patient_email")

            if isinstance(requester, Patient):
                patient_email: str = requester.email
                if target_email and target_email != patient_email:
                    abort(403, message="Un pacient només pot generar un codi QR per a ell mateix.")
            elif isinstance(requester, Doctor):
                if not target_email:
                    abort(422, message="Cal indicar el correu electrònic del pacient.")
                patient_email = target_email
                if patient_email not in requester.patient_emails:
                    abort(403, message="Només pots generar codis QR dels teus pacients.")
            else:
                abort(403, message="No tens permís per generar codis QR.")

            patient_exists = patient_service.patient_exists(patient_email)

            if not patient_exists:
                raise UserNotFoundException("Pacient no trobat.")

            try:
                zone_info = ZoneInfo(data.get("timezone", "Europe/Madrid"))
            except Exception as e:
                self.logger.error("Invalid timezone provided", module="QRResource", metadata={"timezone": data.get("timezone")})
                raise InvalidZoneInfoException("Zona horària invàlida.") from e

            time_delta = timedelta(minutes=10)
            token = user_service.create_access_token(patient_email, time_delta)

            query_params = {
                "timezone": data.get("timezone", "Europe/Madrid"),
                "access_token": token
            }
            url_pdf_endpoint = f"{request.host_url}api/v1/report/{patient_email}?{urlencode(query_params)}"

            file_format = data.get("format", "svg").value
            qr_payload = QRPayload(
                data=url_pdf_endpoint,
                format=file_format,
                fill_color=data.get("fill_color", "#000000"),
                back_color=data.get("back_color", "#FFFFFF"),
                box_size=data.get("box_size", 10),
                border=data.get("border", 4),
            )
            qr, content_type = qr_service.generate_qr_code(qr_payload)

            date = datetime.now(zone_info).strftime("%d/%m/%Y_%H:%M:%S")
            date_for_filename = date.replace("/", "-").replace(":", "-").replace(" ", "_")
            
            return send_file(
                qr,
                mimetype=content_type,
                as_attachment=True,
                download_name=f"qr_{patient_email.split('@')[0]}_{date_for_filename}.{file_format}",
            )
        except DataIntegrityException as e:
            db.session.rollback()
            self.logger.error("Error d'integritat en generar codi QR", module="QRResource", error=e)
            abort(422, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en generar codi QR", module="QRResource", error=e)
            abort(500, message="Error de base de dades en generar el codi QR.")
        except UserNotFoundException as e:
            db.session.rollback()
            self.logger.error("Usuari no trobat en generar codi QR", module="QRResource", error=e)
            abort(404, message=str(e))
        except QRGenerationException as e:
            db.session.rollback()
            self.logger.error("Error en la generació del codi QR", module="QRResource", error=e)
            abort(500, message=str(e))
        except PDFGenerationException as e:
            db.session.rollback()
            self.logger.error("Error en la generació del PDF per al codi QR", module="QRResource", error=e)
            abort(500, message=str(e))
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en generar codi QR", module="QRResource", error=e)
            abort(500, message=f"S'ha produït un error inesperat en generar el codi QR: {str(e)}")
