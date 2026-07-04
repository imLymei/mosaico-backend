import os

from flask_openapi3.blueprint import APIBlueprint
from pydantic import BaseModel, Field
from werkzeug.utils import secure_filename

from models.db import db
from models.user import User
from models.vault import Vault, VaultItem
from routes.auth import _get_user_by_token

VAULT_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vaults")


class CreateVaultRequest(BaseModel):
    name: str | None = None
    icon: str | None = None


class UpdateVaultRequest(BaseModel):
    name: str | None = None
    icon: str | None = None


class UpdateItemRequest(BaseModel):
    name: str = Field(...)


class VaultPathParams(BaseModel):
    vault_id: int = Field(..., description="Vault ID")


class ItemPathParams(BaseModel):
    vault_id: int = Field(..., description="Vault ID")
    item_id: int = Field(..., description="Item ID")


def _get_user_by_id(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def _get_vault_by_id(vault_id: int) -> Vault | None:
    return db.session.get(Vault, vault_id)


def _get_vault_dir(vault_id: int) -> str:
    vault_dir = os.path.join(VAULT_BASE, str(vault_id))
    os.makedirs(vault_dir, exist_ok=True)
    return vault_dir


def _get_current_user() -> User | None:
    from flask import request

    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    return _get_user_by_token(token)


vault_api = APIBlueprint("vault", __name__)


@vault_api.get(
    "/",
    summary="List vaults",
    description="Return all vaults for the authenticated user.",
)
def list_vaults():
    user = _get_current_user()
    if not user:
        return {"error": "Unauthorized"}, 401

    vaults = Vault.query.filter_by(user_id=user.id).all()
    return [v.to_dict() for v in vaults], 200


@vault_api.post(
    "/",
    summary="Create vault",
    description="Create a new vault for the authenticated user.",
)
def create_vault(body: CreateVaultRequest):
    user = _get_current_user()
    if not user:
        return {"error": "Unauthorized"}, 401

    if not body.name or not body.name.strip():
        return {"error": "Vault name is required"}, 400

    vault = Vault(user_id=user.id, name=body.name)
    if body.icon is not None:
        vault.icon = body.icon
    db.session.add(vault)
    db.session.commit()

    return vault.to_dict(), 201


@vault_api.get(
    "/<int:vault_id>",
    summary="Get vault",
    description="Return details for a specific vault.",
)
def get_vault(path: VaultPathParams):
    user = _get_current_user()
    if not user:
        return {"error": "Unauthorized"}, 401

    vault = _get_vault_by_id(path.vault_id)
    if not vault:
        return {"error": "Vault not found"}, 404

    return vault.to_dict(), 200


@vault_api.put(
    "/<int:vault_id>",
    summary="Update vault",
    description="Update the name or icon of a vault.",
)
def update_vault(path: VaultPathParams, body: UpdateVaultRequest):
    user = _get_current_user()
    if not user:
        return {"error": "Unauthorized"}, 401

    vault = _get_vault_by_id(path.vault_id)
    if not vault:
        return {"error": "Vault not found"}, 404

    if vault.user_id != user.id:
        return {"error": "Forbidden"}, 403

    if body.name is not None:
        vault.name = body.name
    if body.icon is not None:
        vault.icon = body.icon
    db.session.commit()

    return vault.to_dict(), 200


@vault_api.delete(
    "/<int:vault_id>",
    summary="Delete vault",
    description="Delete a vault and all its files.",
)
def delete_vault(path: VaultPathParams):
    user = _get_current_user()
    if not user:
        return {"error": "Unauthorized"}, 401

    vault = _get_vault_by_id(path.vault_id)
    if not vault:
        return {"error": "Vault not found"}, 404

    if vault.user_id != user.id:
        return {"error": "Forbidden"}, 403

    vault_dir = os.path.join(VAULT_BASE, str(path.vault_id))
    if os.path.exists(vault_dir):
        for filename in os.listdir(vault_dir):
            filepath = os.path.join(vault_dir, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
        os.rmdir(vault_dir)

    db.session.delete(vault)
    db.session.commit()

    return {"message": "Vault deleted"}, 200


@vault_api.get(
    "/<int:vault_id>/items",
    summary="List items",
    description="Return all items in a vault.",
)
def list_items(path: VaultPathParams):
    user = _get_current_user()
    if not user:
        return {"error": "Unauthorized"}, 401

    vault = _get_vault_by_id(path.vault_id)
    if not vault:
        return {"error": "Vault not found"}, 404

    items = VaultItem.query.filter_by(vault_id=path.vault_id).all()
    return [i.to_dict() for i in items], 200


@vault_api.post(
    "/<int:vault_id>/items",
    summary="Upload item",
    description="Upload a file to a vault.",
)
def upload_item(path: VaultPathParams):
    from flask import request

    user = _get_current_user()
    if not user:
        return {"error": "Unauthorized"}, 401

    vault = _get_vault_by_id(path.vault_id)
    if not vault:
        return {"error": "Vault not found"}, 404

    if vault.user_id != user.id:
        return {"error": "Forbidden"}, 403

    if "file" not in request.files:
        return {"error": "No file provided"}, 400

    file = request.files["file"]
    if not file.filename or file.filename == "":
        return {"error": "Empty filename"}, 400

    name = request.form.get("name", secure_filename(file.filename))
    original_filename = secure_filename(file.filename)

    vault_dir = _get_vault_dir(path.vault_id)
    filepath = os.path.join(vault_dir, original_filename)
    file.save(filepath)

    file_size = os.path.getsize(filepath)
    mime_type = file.content_type or "application/octet-stream"

    item = VaultItem(
        vault_id=path.vault_id,
        name=name,
        filename=original_filename,
        mime_type=mime_type,
        file_size=file_size,
    )
    db.session.add(item)
    db.session.commit()

    return item.to_dict(), 201


@vault_api.get(
    "/<int:vault_id>/items/<int:item_id>",
    summary="Download item",
    description="Download a file from a vault.",
)
def download_item(path: ItemPathParams):
    from flask import request, send_file

    user = _get_current_user()
    if not user:
        return {"error": "Unauthorized"}, 401

    item = db.session.get(VaultItem, path.item_id)
    if not item or item.vault_id != path.vault_id:
        return {"error": "Item not found"}, 404

    filepath = os.path.join(VAULT_BASE, str(path.vault_id), item.filename)
    if not os.path.exists(filepath):
        return {"error": "File not found on disk"}, 404

    inline = request.args.get("inline", "false").lower() == "true"
    return send_file(
        filepath,
        mimetype=item.mime_type,
        as_attachment=not inline,
        download_name=item.filename if not inline else None,
    )


@vault_api.put(
    "/<int:vault_id>/items/<int:item_id>",
    summary="Update item",
    description="Update the name of a vault item.",
)
def update_item(path: ItemPathParams, body: UpdateItemRequest):
    user = _get_current_user()
    if not user:
        return {"error": "Unauthorized"}, 401

    item = db.session.get(VaultItem, path.item_id)
    if not item or item.vault_id != path.vault_id:
        return {"error": "Item not found"}, 404

    vault = db.session.get(Vault, path.vault_id)
    if vault and vault.user_id != user.id:
        return {"error": "Forbidden"}, 403

    if body.name is not None:
        item.name = body.name
    db.session.commit()

    return item.to_dict(), 200


@vault_api.delete(
    "/<int:vault_id>/items/<int:item_id>",
    summary="Delete item",
    description="Delete a file from a vault.",
)
def delete_item(path: ItemPathParams):
    user = _get_current_user()
    if not user:
        return {"error": "Unauthorized"}, 401

    item = db.session.get(VaultItem, path.item_id)
    if not item or item.vault_id != path.vault_id:
        return {"error": "Item not found"}, 404

    vault = db.session.get(Vault, path.vault_id)
    if vault and vault.user_id != user.id:
        return {"error": "Forbidden"}, 403

    filepath = os.path.join(VAULT_BASE, str(path.vault_id), item.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(item)
    db.session.commit()

    return {"message": "Item deleted"}, 200
