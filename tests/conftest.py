import pytest
from sqlalchemy import event
from sqlalchemy.orm import scoped_session, sessionmaker

from app import create_app
from db import db


@pytest.fixture(scope="session")
def app():
    app = create_app("testing_settings")
    with app.app_context():
        db.create_all()
    return app


@pytest.fixture(scope="function")
def db_session(app):
    ctx = app.app_context()
    ctx.push()

    connection = db.engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = scoped_session(SessionLocal)
    db.session = session

    session.begin_nested()

    @event.listens_for(SessionLocal, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        if transaction.is_active:
            transaction.rollback()
        session.remove()
        connection.close()
        ctx.pop()


@pytest.fixture(scope="function")
def client(app, db_session):
    return app.test_client()
