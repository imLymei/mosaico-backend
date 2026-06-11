import os

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from models.db import db
from models.user import User
from models.vault import Vault, VaultItem

VAULT_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vaults")

vault_blueprint = Blueprint("vault", __name__)


def _get_user_by_id(user_id: int):
    return db.session.get(User, user_id)


def _get_vault_by_id(vault_id: int):
    return db.session.get(Vault, vault_id)


def _get_vault_dir(vault_id: int) -> str:
    vault_dir = os.path.join(VAULT_BASE, str(vault_id))
    os.makedirs(vault_dir, exist_ok=True)
    return vault_dir


# === VAULT ROUTES ===


@vault_blueprint.route("/", methods=["GET"])
def list_vaults():
    user_id = request.args.get("userId", type=int)
    if user_id is None:
        return jsonify({"error": "Missing userId query param"}), 400

    user = _get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    vaults = Vault.query.filter_by(user_id=user_id).all()
    return jsonify([v.to_dict() for v in vaults]), 200


@vault_blueprint.route("/", methods=["POST"])
def create_vault():
    data = request.get_json()

    if not all(k in data for k in ("userId", "name")):
        return jsonify({"error": "Invalid json: Body must contain userId and name"}), 400

    user_id = data["userId"]
    name = data["name"]

    user = _get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    vault = Vault(user_id=user_id, name=name)
    db.session.add(vault)
    db.session.commit()

    return jsonify(vault.to_dict()), 201


@vault_blueprint.route("/<int:vault_id>", methods=["GET"])
def get_vault(vault_id: int):
    vault = _get_vault_by_id(vault_id)
    if not vault:
        return jsonify({"error": "Vault not found"}), 404

    return jsonify(vault.to_dict()), 200


@vault_blueprint.route("/<int:vault_id>", methods=["PUT"])
def update_vault(vault_id: int):
    vault = _get_vault_by_id(vault_id)
    if not vault:
        return jsonify({"error": "Vault not found"}), 404

    data = request.get_json()
    if "name" in data:
        vault.name = data["name"]
    db.session.commit()

    return jsonify(vault.to_dict()), 200


@vault_blueprint.route("/<int:vault_id>", methods=["DELETE"])
def delete_vault(vault_id: int):
    vault = _get_vault_by_id(vault_id)
    if not vault:
        return jsonify({"error": "Vault not found"}), 404

    vault_dir = os.path.join(VAULT_BASE, str(vault_id))
    if os.path.exists(vault_dir):
        for filename in os.listdir(vault_dir):
            filepath = os.path.join(vault_dir, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
        os.rmdir(vault_dir)

    db.session.delete(vault)
    db.session.commit()

    return jsonify({"message": "Vault deleted"}), 200


# === VAULT ITEM ROUTES ===


@vault_blueprint.route("/<int:vault_id>/items", methods=["GET"])
def list_items(vault_id: int):
    vault = _get_vault_by_id(vault_id)
    if not vault:
        return jsonify({"error": "Vault not found"}), 404

    items = VaultItem.query.filter_by(vault_id=vault_id).all()
    return jsonify([i.to_dict() for i in items]), 200


@vault_blueprint.route("/<int:vault_id>/items", methods=["POST"])
def upload_item(vault_id: int):
    vault = _get_vault_by_id(vault_id)
    if not vault:
        return jsonify({"error": "Vault not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    name = request.form.get("name", secure_filename(file.filename))
    original_filename = secure_filename(file.filename)

    vault_dir = _get_vault_dir(vault_id)
    filepath = os.path.join(vault_dir, original_filename)
    file.save(filepath)

    file_size = os.path.getsize(filepath)
    mime_type = file.content_type or "application/octet-stream"

    item = VaultItem(
        vault_id=vault_id,
        name=name,
        filename=original_filename,
        mime_type=mime_type,
        file_size=file_size,
    )
    db.session.add(item)
    db.session.commit()

    return jsonify(item.to_dict()), 201


@vault_blueprint.route("/<int:vault_id>/items/<int:item_id>", methods=["GET"])
def download_item(vault_id: int, item_id: int):
    item = db.session.get(VaultItem, item_id)
    if not item or item.vault_id != vault_id:
        return jsonify({"error": "Item not found"}), 404

    filepath = os.path.join(VAULT_BASE, str(vault_id), item.filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found on disk"}), 404

    return send_file(filepath, mimetype=item.mime_type, as_attachment=True, download_name=item.filename)


@vault_blueprint.route("/<int:vault_id>/items/<int:item_id>", methods=["DELETE"])
def delete_item(vault_id: int, item_id: int):
    item = db.session.get(VaultItem, item_id)
    if not item or item.vault_id != vault_id:
        return jsonify({"error": "Item not found"}), 404

    filepath = os.path.join(VAULT_BASE, str(vault_id), item.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(item)
    db.session.commit()

    return jsonify({"message": "Item deleted"}), 200
