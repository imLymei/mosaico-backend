import os
import tempfile
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from main import create_app
from models.db import db
from models.user import User
from models.vault import Vault, VaultItem

TEST_USERNAME = "VAULTTEST"
TEST_EMAIL = "vault@test.com"
TEST_PASSWORD = "Secret123!"


@pytest.fixture
def app() -> Flask:
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def user_id(app: Flask) -> int:
    with app.app_context():
        u = User(username=TEST_USERNAME, email=TEST_EMAIL)
        u.set_password(TEST_PASSWORD)
        db.session.add(u)
        db.session.commit()
        return u.id


# === VAULT CREATION ===


def test_create_vault_success(client: FlaskClient, user_id: int):
    response = client.post(
        "/api/vault/",
        json={"userId": user_id, "name": "My Vault"},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "My Vault"
    assert data["userId"] == user_id


def test_create_vault_missing_fields(client: FlaskClient):
    response = client.post("/api/vault/", json={})
    assert response.status_code == 400


def test_create_vault_user_not_found(client: FlaskClient):
    response = client.post("/api/vault/", json={"userId": 99999, "name": "Ghost"})
    assert response.status_code == 404


def test_create_vault_multiple_for_same_user(client: FlaskClient, user_id: int):
    r1 = client.post("/api/vault/", json={"userId": user_id, "name": "Vault 1"})
    r2 = client.post("/api/vault/", json={"userId": user_id, "name": "Vault 2"})
    assert r1.status_code == 201
    assert r2.status_code == 201


# === VAULT LISTING ===


def test_list_vaults_success(client: FlaskClient, user_id: int):
    client.post("/api/vault/", json={"userId": user_id, "name": "Vault A"})
    client.post("/api/vault/", json={"userId": user_id, "name": "Vault B"})

    response = client.get(f"/api/vault/?userId={user_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2


def test_list_vaults_user_not_found(client: FlaskClient):
    response = client.get("/api/vault/?userId=99999")
    assert response.status_code == 404


def test_list_vaults_missing_user_id(client: FlaskClient):
    response = client.get("/api/vault/")
    assert response.status_code == 400


# === VAULT GET ===


def test_get_vault_success(client: FlaskClient, user_id: int):
    vault_resp = client.post("/api/vault/", json={"userId": user_id, "name": "Get Me"})
    vault_id = vault_resp.get_json()["id"]

    response = client.get(f"/api/vault/{vault_id}")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Get Me"


def test_get_vault_not_found(client: FlaskClient):
    response = client.get("/api/vault/99999")
    assert response.status_code == 404


# === VAULT UPDATE ===


def test_update_vault_success(client: FlaskClient, user_id: int):
    vault_resp = client.post("/api/vault/", json={"userId": user_id, "name": "Old Name"})
    vault_id = vault_resp.get_json()["id"]

    response = client.put(f"/api/vault/{vault_id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.get_json()["name"] == "New Name"


def test_update_vault_not_found(client: FlaskClient):
    response = client.put("/api/vault/99999", json={"name": "X"})
    assert response.status_code == 404


# === VAULT DELETE ===


def test_delete_vault_success(client: FlaskClient, user_id: int):
    vault_resp = client.post("/api/vault/", json={"userId": user_id, "name": "ToDelete"})
    vault_id = vault_resp.get_json()["id"]

    response = client.delete(f"/api/vault/{vault_id}")
    assert response.status_code == 200

    get_resp = client.get(f"/api/vault/{vault_id}")
    assert get_resp.status_code == 404


def test_delete_vault_not_found(client: FlaskClient):
    response = client.delete("/api/vault/99999")
    assert response.status_code == 404


# === VAULT ITEM UPLOAD ===


def test_upload_item_success(client: FlaskClient, user_id: int):
    vault_resp = client.post("/api/vault/", json={"userId": user_id, "name": "Item Vault"})
    vault_id = vault_resp.get_json()["id"]

    data = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    data.write(b"\x89PNG\r\n\x1a\n")
    data.close()

    with open(data.name, "rb") as f:
        response = client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "test.png"), "name": "Test Image"},
            content_type="multipart/form-data",
        )

    assert response.status_code == 201
    item_data = response.get_json()
    assert item_data["name"] == "Test Image"
    assert item_data["vaultId"] == vault_id
    assert item_data["fileSize"] > 0

    os.unlink(data.name)


def test_upload_item_no_file(client: FlaskClient, user_id: int):
    vault_resp = client.post("/api/vault/", json={"userId": user_id, "name": "X"})
    vault_id = vault_resp.get_json()["id"]

    response = client.post(f"/api/vault/{vault_id}/items", data={})
    assert response.status_code == 400


def test_upload_item_vault_not_found(client: FlaskClient):
    response = client.post(
        "/api/vault/99999/items",
        data={"file": (b"", "test.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 404


# === VAULT ITEM LISTING ===


def test_list_items_success(client: FlaskClient, user_id: int):
    vault_resp = client.post("/api/vault/", json={"userId": user_id, "name": "ItemList"})
    vault_id = vault_resp.get_json()["id"]

    data = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    data.write(b"\x89PNG\r\n\x1a\n")
    data.close()

    with open(data.name, "rb") as f:
        client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "one.png"), "name": "One"},
            content_type="multipart/form-data",
        )

    with open(data.name, "rb") as f:
        client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "two.png"), "name": "Two"},
            content_type="multipart/form-data",
        )

    os.unlink(data.name)

    response = client.get(f"/api/vault/{vault_id}/items")
    assert response.status_code == 200
    assert len(response.get_json()) == 2


# === VAULT ITEM DOWNLOAD ===


def test_download_item_success(client: FlaskClient, user_id: int):
    vault_resp = client.post("/api/vault/", json={"userId": user_id, "name": "Download"})
    vault_id = vault_resp.get_json()["id"]

    data = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    data.write(b"\x89PNG\r\n\x1a\n")
    data.close()

    with open(data.name, "rb") as f:
        upload_resp = client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "dl.png"), "name": "DL"},
            content_type="multipart/form-data",
        )

    os.unlink(data.name)

    item_id = upload_resp.get_json()["id"]
    response = client.get(f"/api/vault/{vault_id}/items/{item_id}")
    assert response.status_code == 200


def test_download_item_not_found(client: FlaskClient, user_id: int):
    vault_resp = client.post("/api/vault/", json={"userId": user_id, "name": "X"})
    vault_id = vault_resp.get_json()["id"]

    response = client.get(f"/api/vault/{vault_id}/items/99999")
    assert response.status_code == 404


# === VAULT ITEM DELETE ===


def test_delete_item_success(client: FlaskClient, user_id: int):
    vault_resp = client.post("/api/vault/", json={"userId": user_id, "name": "ItemDel"})
    vault_id = vault_resp.get_json()["id"]

    data = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    data.write(b"\x89PNG\r\n\x1a\n")
    data.close()

    with open(data.name, "rb") as f:
        upload_resp = client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "del.png"), "name": "Del"},
            content_type="multipart/form-data",
        )

    os.unlink(data.name)
    item_id = upload_resp.get_json()["id"]

    response = client.delete(f"/api/vault/{vault_id}/items/{item_id}")
    assert response.status_code == 200

    get_resp = client.get(f"/api/vault/{vault_id}/items/{item_id}")
    assert get_resp.status_code == 404


def test_delete_item_not_found(client: FlaskClient, user_id: int):
    vault_resp = client.post("/api/vault/", json={"userId": user_id, "name": "X"})
    vault_id = vault_resp.get_json()["id"]

    response = client.delete(f"/api/vault/{vault_id}/items/99999")
    assert response.status_code == 404
