import pytest
from flask import Flask
from flask.testing import FlaskClient

from main import create_app
from models.db import db
from models.user import User

TEST_USERNAME = "TEST123"
TEST_EMAIL = "TEST@test.com"
TEST_PASSWORD = "SECRET123"


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


# === USER LOGIC ===


def test_create_user(app: Flask):
    user = User(username=TEST_USERNAME, email=TEST_EMAIL)
    user.set_password(TEST_PASSWORD)

    with app.app_context():
        db.session.add(user)
        db.session.commit()

    result = User.query.filter_by(username=TEST_USERNAME).first()

    assert result is not None
    assert result.check_password(TEST_PASSWORD)
    assert result.to_dict()["username"] == TEST_USERNAME


# === REGISTER LOGIC ===


def test_register_missing_fields(client: FlaskClient):
    body_array = [
        {"email": TEST_EMAIL, "password": TEST_PASSWORD},
        {"username": TEST_USERNAME, "password": TEST_PASSWORD},
        {"username": TEST_USERNAME, "email": TEST_EMAIL},
        {"username": TEST_USERNAME},
        {"email": TEST_EMAIL},
        {"password": TEST_PASSWORD},
        {},
        None,
    ]

    for index in range(len(body_array)):
        body = body_array[index]
        response = client.post("/api/auth/register", json=body)

        assert response.status_code == 400 or response.status_code == 415


def test_register_success(client: FlaskClient):
    response = client.post(
        "/api/auth/register",
        json={
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 201


# === LOGIN LOGIC ===


def test_login_missing_fields(client: FlaskClient):
    response_username = client.post("/api/auth/login", json={"username": TEST_USERNAME})
    response_password = client.post("/api/auth/login", json={"password": TEST_PASSWORD})

    assert response_username.status_code == 400
    assert response_password.status_code == 400


def test_login_user_not_found(client: FlaskClient):
    response = client.post("/api/auth/login", json={"username": "x", "password": "x"})
    assert response.status_code == 404


def test_login_wrong_password(app: Flask, client: FlaskClient):
    with app.app_context():
        user = User(username=TEST_USERNAME, email=TEST_EMAIL)
        user.set_password(TEST_PASSWORD)

        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/api/auth/login", json={"username": TEST_USERNAME, "password": "x"}
    )
    assert response.status_code == 404


def test_login_success(app: Flask, client: FlaskClient):
    with app.app_context():
        user = User(username=TEST_USERNAME, email=TEST_EMAIL)
        user.set_password(TEST_PASSWORD)

        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["username"] == TEST_USERNAME
    assert data["email"] == TEST_EMAIL
