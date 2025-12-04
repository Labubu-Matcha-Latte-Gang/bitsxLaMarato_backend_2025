import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from db import db


@pytest.fixture(scope="session")
def app():
    app = create_app("testing_settings")
    with app.app_context():
        # Clean legacy tables that may not be in metadata to avoid FK issues on drop_all
        with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(sa.text("DROP TABLE IF EXISTS activities_completed CASCADE"))
        # Ensure schema matches current models (drops existing tables in test DB)
        db.drop_all()
        db.create_all()
    return app


@pytest.fixture(scope="session")
def db_connection(app):
    with app.app_context():
        connection = db.engine.connect()
    yield connection
    connection.close()


@pytest.fixture(scope="function")
def db_session(app, db_connection):
    transaction = db_connection.begin()
    session_factory = sessionmaker(bind=db_connection)
    session = scoped_session(session_factory)
    db.session = session

    session.begin_nested()

    @event.listens_for(session(), "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            session.begin_nested()

    ctx = app.app_context()
    ctx.push()

    yield session

    transaction.rollback()
    session.remove()
    ctx.pop()


@pytest.fixture(scope="function")
def client(app, db_session):
    return app.test_client()
