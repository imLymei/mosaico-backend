import re

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

    if len(username) < 4:
        return jsonify({"error": "Invalid username"}), 400
    if not re.match(
        r"^[A-Za-z0-9_%+-]+(\.[A-Za-z0-9_%+-]+)*@([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}$",
        email,
    ):
        return jsonify({"error": "Invalid email format"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username is taken"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is taken"}), 409

    user = User(username, email)
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201


@auth_blueprint.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not all(k in data for k in ("username", "password")):
        return jsonify(
            {"error": "Invalid json: Body must contain username and password"}
        ), 400

    username = data["username"]
    password = data["password"]

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 404

    if not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 404

    return jsonify(user.to_dict()), 200
