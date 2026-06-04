from flask import Blueprint, jsonify, request

from models.db import db
from models.user import User

auth_blueprint = Blueprint("auth", __name__)


@auth_blueprint.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not all(k in data for k in ("username", "email", "password")):
        return jsonify(
            {"error": "Invalid json: Body must contain username, email and password"}
        ), 400

    username = data["username"]
    email = data["email"]

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username is taken"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is taken"}), 409

    user = User(username, email)
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201
