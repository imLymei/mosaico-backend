from typing import Generator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from main import create_app
from models.db import db
from models.user import User

TEST_USERNAME = "TEST123"
TEST_EMAIL = "TEST@test.com"
TEST_PASSWORD = "Secret123!"


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    app = create_app("sqlite:///:memory:")
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
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


def test_register_username_min_length(client: FlaskClient):
    body = {
        "username": "1234",
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    }

    firstResponse = client.post("/api/auth/register", json=body)
    assert firstResponse.status_code == 201

    body["username"] = "123"
    body["email"] += ".two"

    firstResponse = client.post("/api/auth/register", json=body)
    assert firstResponse.status_code == 400


def test_register_invalid_email(client: FlaskClient):
    invalid_emails = [
        ".two",
        "plainaddress",
        "@missingusername.com",
        "noat-sign.com",
        "user@",
        "user@.com",
        "user@com",
        "user name@domain.com",
        "user@domain",
        "user@.domain.com",
        "user@domain..com",
        "user@domain.c",
        "user@-domain.com",
        "user@domain-.com",
        "user name",
        "",
        "   ",
        "user@domain.com.",
        ".user@domain.com",
        "user.@domain.com.",
    ]

    valid_emails = [
        "user@domain.com",
        "first.last@domain.co.uk",
        "user123@test.org",
        "name+tag@example.com",
        "name%20@example.com",
        "user_name@sub.domain.com",
        "a@b.cd",
    ]

    for email in invalid_emails:
        body = {
            "username": f"invalid_user_{email.replace(' ', '_')[:20]}",
            "email": email,
            "password": TEST_PASSWORD,
        }
        response = client.post("/api/auth/register", json=body)
        assert response.status_code == 400

    for email in valid_emails:
        body = {
            "username": f"valid_user_{email.split('@')[0][:20]}",
            "email": email,
            "password": TEST_PASSWORD,
        }
        response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201


def test_register_weak_password(client: FlaskClient):
    weak_passwords = [
        "short1!",
        "NoSpecialChar123",
        "nouppercase123!",
        "NOLOWERCASE123!",
        "NoNumbers!@#$%",
        "Password!",
        "",
        "a" * 7,
        "a" * 100,
        "password123!",
        "PASSWORD123!",
        "P@ss",
        "P@ssword",
        "12345678",
        "aaaaaaaa!",
        "AAAAAAAA!",
        "         !",
    ]

    valid_passwords = [
        "Secret123!",
        "Str0ng!Pass",
        "MyP@ssw0rd!",
        "C0mpl3x#Pass",
        "Ab1!Cd2@Ef3#",
        "Test1234!",
        "Xy9#Zw4@Km1!",
        "Pass1!word2@",
        "aB3$dE5%fG7&",
        "Qw!er123Ty",
        "12345678!aA",
    ]

    for idx, password in enumerate(weak_passwords):
        body = {
            "username": f"weak_pw_user_{idx}_{len(password)}",
            "email": f"weak_pw_{idx}_{len(password)}@test.com",
            "password": password,
        }
        response = client.post("/api/auth/register", json=body)
        assert response.status_code == 400, f"Expected 400 for weak password '{password[:20]}...', got {response.status_code}"

    for idx, password in enumerate(valid_passwords):
        body = {
            "username": f"valid_pw_user_{idx}_{len(password)}",
            "email": f"valid_pw_{idx}_{len(password)}@test.com",
            "password": password,
        }
        response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, f"Expected 201 for valid password '{password[:20]}...', got {response.status_code}"


def test_register_duplicated_username(client: FlaskClient):
    body = {
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    }

    firstResponse = client.post("/api/auth/register", json=body)
    assert firstResponse.status_code == 201

    body["email"] += ".two"

    secondResponse = client.post("/api/auth/register", json=body)
    assert secondResponse.status_code == 409


def test_register_duplicated_email(client: FlaskClient):
    body = {
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    }

    firstResponse = client.post("/api/auth/register", json=body)
    assert firstResponse.status_code == 201

    body["username"] += "_two"

    secondResponse = client.post("/api/auth/register", json=body)
    assert secondResponse.status_code == 409


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
    assert "token" in data
    assert len(data["token"]) > 0
