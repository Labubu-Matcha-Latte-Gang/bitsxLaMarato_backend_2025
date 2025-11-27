import pytest
from sqlalchemy import event

from app import create_app
from db import db
from tests.base_test import BaseTest


@pytest.fixture(scope="session")
def app():
    app = create_app("testing_settings")
    with app.app_context():
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
    options = dict(bind=db_connection, binds={})
    session = db.create_scoped_session(options=options)
    db.session = session

    session.begin_nested()

    @event.listens_for(session(), "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            session.begin_nested()

    ctx = app.app_context()
    ctx.push()

    yield session

    session.remove()
    transaction.rollback()
    ctx.pop()


@pytest.fixture(scope="function")
def client(app, db_session):
    return app.test_client()


@pytest.fixture(scope="function")
def helper(app, client, db_session):
    return BaseTest(app, client, db_session)
