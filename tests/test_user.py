import pytest
from flask import Flask
from flask.testing import FlaskClient

from main import create_app
from models.db import db
from models.user import User


@pytest.fixture
def app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app: Flask):
    return app.test_client()


def test_create_user(app: Flask):
    TEST_USERNAME = "TEST123"
    TEST_PASSWORD = "SECRET123"

    user = User(username=TEST_USERNAME, email="test.123@test.com")
    user.set_password(TEST_PASSWORD)

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    result = User.query.filter_by(username=TEST_USERNAME).first()

    assert result is not None
    assert result.check_password(TEST_PASSWORD)
    assert result.to_dict()["username"] == TEST_USERNAME


def test_register_route(client: FlaskClient):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "bob",
            "email": "bob@test.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201
