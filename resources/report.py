from flask import send_file
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from sqlalchemy.exc import IntegrityError
from zoneinfo import ZoneInfo

from db import db
from helpers.debugger.logger import AbstractLogger
from helpers.exceptions.pdf_exceptions import InvalidZoneInfoException, PDFGenerationException
from helpers.exceptions.integrity_exceptions import DataIntegrityException
from helpers.exceptions.user_exceptions import ExpiredTokenException, InvalidTokenException
from application.container import ServiceFactory
from io import BytesIO
from schemas import (
    PatientEmailPathSchema,
    ReportGenerateSchema,
)

blp = Blueprint('report', __name__, description="Generació d'informes mèdics de pacients.")


@blp.route('/<string:email>')
class ReportResource(MethodView):
    """
    Endpoints per obtenir informes mèdics de progressió de pacients.
    """

    logger = AbstractLogger.get_instance()

    @blp.arguments(PatientEmailPathSchema, location="path")
    @blp.arguments(ReportGenerateSchema, location="query")
    @blp.doc(
        summary="Obtenir l'informe mèdic d'un pacient.",
        description=(
            "Els administradors poden obtenir qualsevol pacient; els metges només si hi estan assignats; "
            "els pacients poden obtenir el seu propi informe."
        ),
        security=[]
    )
    @blp.response(200, description="Informe mèdic generat correctament.", content_type="application/pdf")
    @blp.response(400, description="Zona horària invàlida.")
    @blp.response(401, description="Falta o és invàlid el JWT.")
    @blp.response(403, description="L'usuari autenticat no pot veure aquest pacient.")
    @blp.response(404, description="Pacient no trobat.")
    @blp.response(409, description="S'ha detectat un conflicte de rol d'usuari.")
    @blp.response(500, description="Error inesperat del servidor en recuperar el pacient.")
    def get(self, path_args: dict, query_params: dict, **kwargs):
        """
        Obté un informe mèdic de progressió d'un pacient en format PDF.
        """
        try:
            service_factory = ServiceFactory.get_instance()
            pdf_service = service_factory.build_pdf_generation_service()
            user_service = service_factory.build_user_service()
            patient_service = service_factory.build_patient_service()

            patient_email: str = path_args["email"]
            patient = patient_service.get_patient(patient_email)

            token = query_params.get("access_token")
            if not token:
                raise InvalidTokenException("Cal un token vàlid per accedir a l'informe.")
            
            current_user = user_service.get_user_by_token(token)

            patient_data = user_service.get_patient_data(current_user, patient, graph_format="png")

            try:
                zone_info = ZoneInfo(query_params.get("timezone", "Europe/Madrid"))
            except Exception as e:
                self.logger.error("Invalid timezone provided", module="ReportResource", metadata={"timezone": query_params.get("timezone")})
                raise InvalidZoneInfoException("Zona horària invàlida.") from e
            
            pdf_bytes, date = pdf_service.generate_patient_report(patient_data, zone_info)

            patient_name = f"{patient.name}_{patient.surname}"
            date_for_filename = date.replace("/", "-")

            pdf_file = BytesIO(pdf_bytes)

            return send_file(
                    pdf_file,
                    mimetype="application/pdf",
                    as_attachment=True,
                    download_name=f"{patient_name}_report_{date_for_filename}.pdf",
                )
        except ExpiredTokenException as e:
            self.logger.warning("Expired token when accessing patient report", module="ReportResource", error=e)
            abort(401, message="El token ha caducat. Torna a iniciar sessió per generar l'informe.")
        except InvalidTokenException as e:
            self.logger.warning("Invalid token when accessing patient report", module="ReportResource", error=e)
            abort(401, message=str(e))
        except DataIntegrityException as e:
            self.logger.error("Data integrity error", module="ReportResource", error=e)
            abort(409, message=str(e))
        except PermissionError as e:
            self.logger.error("Permission denied to access patient report", module="ReportResource", error=e)
            abort(403, message=str(e))
        except IntegrityError as e:
            db.session.rollback()
            self.logger.error("Error de base de dades en generar l'informe", module="ReportResource", error=e)
            abort(500, message="Error de base de dades en generar l'informe")
        except InvalidZoneInfoException as e:
            self.logger.error("Invalid timezone error", module="ReportResource", error=e)
            abort(400, message=str(e))
        except PDFGenerationException as e:
            db.session.rollback()
            self.logger.error("Error en la generació del PDF per a l'informe", module="ReportResource", error=e)
            abort(500, message=str(e))
        except Exception as e:
            db.session.rollback()
            self.logger.error("Error inesperat en generar informe mèdic", module="ReportResource", error=e)
            abort(500, message=f"S'ha produït un error inesperat en generar l'informe: {str(e)}")
