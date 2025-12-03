from __future__ import annotations

from db import db
from domain.unit_of_work import IUnitOfWork


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
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
