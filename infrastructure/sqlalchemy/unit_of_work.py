from __future__ import annotations

from db import db
from domain.unit_of_work import IUnitOfWork
from helpers.exceptions.integrity_exceptions import DataIntegrityException
from sqlalchemy.exc import IntegrityError


class SQLAlchemyUnitOfWork(IUnitOfWork):
    """
    Unit of Work implementation backed by SQLAlchemy sessions.
    """

    def __init__(self, session=None):
        self.session = session or db.session

    def __enter__(self) -> "SQLAlchemyUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            self.rollback()
        else:
            try:
                self.commit()
            except Exception:
                self.rollback()
                raise

    def commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise map_integrity_error(exc) from exc

    def rollback(self) -> None:
        self.session.rollback()


def map_integrity_error(exc: IntegrityError) -> DataIntegrityException:
    """
    Converteix errors d'integritat de la base de dades en excepcions de domini amb missatges en català.
    """
    diag = getattr(exc.orig, "diag", None)  # type: ignore[attr-defined]
    constraint = getattr(diag, "constraint_name", None) if diag else None
    column = getattr(diag, "column_name", None) if diag else None
    table = getattr(diag, "table_name", None) if diag else None
    primary = getattr(diag, "message_primary", "") if diag else ""
    detail = getattr(diag, "message_detail", "") if diag else ""

    constraint_messages = {
        # Comprovacions de rang
        "check_activity_difficulty_range": "La dificultat de l'activitat ha d'estar entre 0 i 5.",
        "check_question_difficulty_range": "La dificultat de la pregunta ha d'estar entre 0 i 5.",
        "ck_patient_age_range": "L'edat del pacient ha d'estar entre 0 i 120 anys.",
        "ck_patient_height_range": "L'alçada del pacient ha d'estar entre 0 i 250 centímetres.",
        "ck_patient_weight_range": "El pes del pacient ha d'estar entre 0 i 600 quilograms.",
        "check_activity_completed_score_range": "La puntuació ha d'estar entre 0 i 10.",
        "ck_users_role_not_null": "El rol de l'usuari és obligatori.",
        # Claus úniques i primary keys
        "activities_title_key": "Ja existeix una activitat amb aquest títol.",
        "questions_text_key": "Ja existeix una pregunta amb aquest enunciat.",
        "users_pkey": "Ja existeix un usuari amb aquest correu.",
        "patients_pkey": "Ja existeix un pacient amb aquest correu.",
        "doctors_pkey": "Ja existeix un metge amb aquest correu.",
        "admins_pkey": "Ja existeix un administrador amb aquest correu.",
        "user_codes_pkey": "Ja existeix un codi actiu per a aquest usuari.",
        "doctor_patient_pkey": "Ja existeix una associació entre aquest metge i aquest pacient.",
        "questions_answered_pkey": "Ja s'ha registrat aquesta pregunta com a contestada pel pacient.",
        "activities_completed_pkey": "Ja s'ha registrat aquesta activitat com a completada pel pacient.",
    }

    raw_message = str(getattr(exc, "orig", exc))

    if constraint and constraint in constraint_messages:
        return DataIntegrityException(constraint_messages[constraint])

    lowered_primary = (primary or "").lower()
    detail_lower = (detail or "").lower()

    if column and ("null value" in lowered_primary or "not-null" in lowered_primary):
        return DataIntegrityException(f"El camp '{column}' és obligatori.")

    if "duplicate key value" in lowered_primary or "duplicate" in detail_lower:
        if table == "activities":
            return DataIntegrityException("Ja existeix una activitat amb aquestes dades.")
        if table == "questions":
            return DataIntegrityException("Ja existeix una pregunta amb aquestes dades.")
        if table in {"users", "patients", "doctors", "admins"}:
            return DataIntegrityException("Ja existeix un usuari amb aquest correu.")
        return DataIntegrityException("Ja existeix un registre amb aquest identificador.")

    # Fallback per a motors sense diag (p.ex. SQLite)
    for key, msg in constraint_messages.items():
        if key in raw_message:
            return DataIntegrityException(msg)

    if "not null constraint failed" in raw_message.lower():
        # Format SQLite: NOT NULL constraint failed: table.column
        if "." in raw_message:
            parts = raw_message.split(":")[-1].strip().split(".")
            if len(parts) == 2:
                _, col = parts
                return DataIntegrityException(f"El camp '{col}' és obligatori.")

    if constraint:
        return DataIntegrityException(f"Les dades no compleixen el requisit d'integritat '{constraint}'.")

    return DataIntegrityException("Les dades no compleixen els requisits d'integritat.")
