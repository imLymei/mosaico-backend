import re
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, jsonify, request

from models.db import db
from models.user import User

auth_blueprint = Blueprint("auth", __name__)


def _get_user_by_token(token: str | None) -> User | None:
    if not token:
        return None
    user = User.query.filter_by(session_token=token).first()
    if user and user.is_token_valid():
        return user
    if user:
        user.clear_session_token()
        db.session.commit()
    return None


@auth_blueprint.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if data is None:
        return jsonify(
            {"error": "Invalid json: Body must contain username, email and password"}
        ), 400

    if not all(k in data for k in ("username", "email", "password")):
        return jsonify(
            {"error": "Invalid json: Body must contain username, email and password"}
        ), 400

    username: str = data["username"]
    email: str = data["email"]
    password: str = data["password"]

    if len(username) < 4:
        return jsonify({"error": "Invalid username"}), 400
    if not re.match(
        r"^[A-Za-z0-9_%+-]+(\.[A-Za-z0-9_%+-]+)*@([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}$",
        email,
    ):
        return jsonify({"error": "Invalid email format"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if not re.search(r"[A-Z]", password):
        return jsonify(
            {"error": "Password must contain at least one uppercase letter"}
        ), 400
    if not re.search(r"[a-z]", password):
        return jsonify(
            {"error": "Password must contain at least one lowercase letter"}
        ), 400
    if not re.search(r"[0-9]", password):
        return jsonify({"error": "Password must contain at least one number"}), 400
    if not re.search(r"[!@#$%^&*_+,.?\":{}|<>-]", password):
        return jsonify(
            {"error": "Password must contain at least one special character"}
        ), 400

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
    if data is None:
        return jsonify(
            {"error": "Invalid json: Body must contain username and password"}
        ), 400

    if not all(k in data for k in ("username", "password")):
        return jsonify(
            {"error": "Invalid json: Body must contain username and password"}
        ), 400

    username: str = data["username"]
    password: str = data["password"]

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 404

    if not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 404

    user.generate_session_token()
    db.session.commit()

    user_dict = user.to_dict()
    user_dict["token"] = user.session_token
    return jsonify(user_dict), 200


@auth_blueprint.route("/logout", methods=["POST"])
def logout():
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    user = _get_user_by_token(token)
    if user:
        user.clear_session_token()
        db.session.commit()
    return jsonify({"message": "Logged out"}), 200
