import os
import tempfile
from typing import Generator

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


@pytest.fixture
def user_id(app: Flask) -> int:
    with app.app_context():
        u = User(username=TEST_USERNAME, email=TEST_EMAIL)
        u.set_password(TEST_PASSWORD)
        db.session.add(u)
        db.session.commit()
        return u.id


@pytest.fixture
def auth_token(app: Flask, client: FlaskClient) -> str:
    with app.app_context():
        u = User(username=TEST_USERNAME, email=TEST_EMAIL)
        u.set_password(TEST_PASSWORD)
        db.session.add(u)
        db.session.commit()
        u.generate_session_token()
        db.session.commit()
        return u.session_token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# === VAULT CREATION ===


def test_create_vault_success(client: FlaskClient, auth_token: str):
    response = client.post(
        "/api/vault/",
        json={"name": "My Vault"},
        headers=_headers(auth_token),
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "My Vault"
    assert data["userId"] > 0


def test_create_vault_missing_fields(client: FlaskClient):
    response = client.post("/api/vault/", json={})
    assert response.status_code == 401


def test_create_vault_user_not_found(client: FlaskClient):
    response = client.post("/api/vault/", json={"name": "Ghost"})
    assert response.status_code == 401


def test_create_vault_multiple_for_same_user(client: FlaskClient, auth_token: str):
    r1 = client.post(
        "/api/vault/", json={"name": "Vault 1"}, headers=_headers(auth_token)
    )
    r2 = client.post(
        "/api/vault/", json={"name": "Vault 2"}, headers=_headers(auth_token)
    )
    assert r1.status_code == 201
    assert r2.status_code == 201


# === VAULT LISTING ===


def test_list_vaults_success(client: FlaskClient, auth_token: str):
    client.post("/api/vault/", json={"name": "Vault A"}, headers=_headers(auth_token))
    client.post("/api/vault/", json={"name": "Vault B"}, headers=_headers(auth_token))

    response = client.get("/api/vault/", headers=_headers(auth_token))
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2


def test_list_vaults_user_not_found(client: FlaskClient):
    response = client.get("/api/vault/")
    assert response.status_code == 401


def test_list_vaults_missing_user_id(client: FlaskClient):
    response = client.get("/api/vault/")
    assert response.status_code == 401


# === VAULT GET ===


def test_get_vault_success(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "Get Me"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    response = client.get(f"/api/vault/{vault_id}", headers=_headers(auth_token))
    assert response.status_code == 200
    assert response.get_json()["name"] == "Get Me"


def test_get_vault_not_found(client: FlaskClient, auth_token: str):
    response = client.get("/api/vault/99999", headers=_headers(auth_token))
    assert response.status_code == 404


# === VAULT UPDATE ===


def test_update_vault_success(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "Old Name"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    response = client.put(
        f"/api/vault/{vault_id}",
        json={"name": "New Name"},
        headers=_headers(auth_token),
    )
    assert response.status_code == 200
    assert response.get_json()["name"] == "New Name"


def test_update_vault_not_found(client: FlaskClient, auth_token: str):
    response = client.put(
        "/api/vault/99999", json={"name": "X"}, headers=_headers(auth_token)
    )
    assert response.status_code == 404


# === VAULT DELETE ===


def test_delete_vault_success(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "ToDelete"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    response = client.delete(f"/api/vault/{vault_id}", headers=_headers(auth_token))
    assert response.status_code == 200

    get_resp = client.get(f"/api/vault/{vault_id}", headers=_headers(auth_token))
    assert get_resp.status_code == 404


def test_delete_vault_not_found(client: FlaskClient, auth_token: str):
    response = client.delete("/api/vault/99999", headers=_headers(auth_token))
    assert response.status_code == 404


# === VAULT ITEM UPLOAD ===


def test_upload_item_success(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "Item Vault"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    data = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    data.write(b"\x89PNG\r\n\x1a\n")
    data.close()

    with open(data.name, "rb") as f:
        response = client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "test.png"), "name": "Test Image"},
            content_type="multipart/form-data",
            headers=_headers(auth_token),
        )

    assert response.status_code == 201
    item_data = response.get_json()
    assert item_data["name"] == "Test Image"
    assert item_data["vaultId"] == vault_id
    assert item_data["fileSize"] > 0

    os.unlink(data.name)


def test_upload_item_no_file(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "X"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    response = client.post(
        f"/api/vault/{vault_id}/items", data={}, headers=_headers(auth_token)
    )
    assert response.status_code == 400


def test_upload_item_vault_not_found(client: FlaskClient, auth_token: str):
    response = client.post(
        "/api/vault/99999/items",
        data={"file": (b"", "test.png")},
        content_type="multipart/form-data",
        headers=_headers(auth_token),
    )
    assert response.status_code == 404


# === VAULT ITEM LISTING ===


def test_list_items_success(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "ItemList"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    data = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    data.write(b"\x89PNG\r\n\x1a\n")
    data.close()

    with open(data.name, "rb") as f:
        client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "one.png"), "name": "One"},
            content_type="multipart/form-data",
            headers=_headers(auth_token),
        )

    with open(data.name, "rb") as f:
        client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "two.png"), "name": "Two"},
            content_type="multipart/form-data",
            headers=_headers(auth_token),
        )

    os.unlink(data.name)

    response = client.get(f"/api/vault/{vault_id}/items", headers=_headers(auth_token))
    assert response.status_code == 200
    assert len(response.get_json()) == 2


# === VAULT ITEM DOWNLOAD ===


def test_download_item_success(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "Download"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    data = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    data.write(b"\x89PNG\r\n\x1a\n")
    data.close()

    with open(data.name, "rb") as f:
        upload_resp = client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "dl.png"), "name": "DL"},
            content_type="multipart/form-data",
            headers=_headers(auth_token),
        )

    os.unlink(data.name)

    item_id = upload_resp.get_json()["id"]
    response = client.get(
        f"/api/vault/{vault_id}/items/{item_id}", headers=_headers(auth_token)
    )
    assert response.status_code == 200


def test_download_item_not_found(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "X"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    response = client.get(
        f"/api/vault/{vault_id}/items/99999", headers=_headers(auth_token)
    )
    assert response.status_code == 404


def test_download_item_without_auth_returns_401(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "X"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    data = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    data.write(b"\x89PNG\r\n\x1a\n")
    data.close()

    with open(data.name, "rb") as f:
        upload_resp = client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "test.png"), "name": "Test"},
            content_type="multipart/form-data",
            headers=_headers(auth_token),
        )

    os.unlink(data.name)
    item_id = upload_resp.get_json()["id"]

    response = client.get(f"/api/vault/{vault_id}/items/{item_id}")
    assert response.status_code == 401


def test_download_item_with_inline_param_returns_200(
    client: FlaskClient, auth_token: str
):
    vault_resp = client.post(
        "/api/vault/", json={"name": "Inline"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    data = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    data.write(b"\x89PNG\r\n\x1a\n")
    data.close()

    with open(data.name, "rb") as f:
        upload_resp = client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "inline.png"), "name": "Inline"},
            content_type="multipart/form-data",
            headers=_headers(auth_token),
        )

    os.unlink(data.name)
    item_id = upload_resp.get_json()["id"]

    response = client.get(
        f"/api/vault/{vault_id}/items/{item_id}?inline=true",
        headers=_headers(auth_token),
    )
    assert response.status_code == 200
    assert "inline" in response.headers.get("Content-Disposition", "")


# === VAULT ITEM DELETE ===


def test_delete_item_success(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "ItemDel"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    data = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    data.write(b"\x89PNG\r\n\x1a\n")
    data.close()

    with open(data.name, "rb") as f:
        upload_resp = client.post(
            f"/api/vault/{vault_id}/items",
            data={"file": (f, "del.png"), "name": "Del"},
            content_type="multipart/form-data",
            headers=_headers(auth_token),
        )

    os.unlink(data.name)
    item_id = upload_resp.get_json()["id"]

    response = client.delete(
        f"/api/vault/{vault_id}/items/{item_id}", headers=_headers(auth_token)
    )
    assert response.status_code == 200

    get_resp = client.get(
        f"/api/vault/{vault_id}/items/{item_id}", headers=_headers(auth_token)
    )
    assert get_resp.status_code == 404


def test_delete_item_not_found(client: FlaskClient, auth_token: str):
    vault_resp = client.post(
        "/api/vault/", json={"name": "X"}, headers=_headers(auth_token)
    )
    vault_id = vault_resp.get_json()["id"]

    response = client.delete(
        f"/api/vault/{vault_id}/items/99999", headers=_headers(auth_token)
    )
    assert response.status_code == 404
