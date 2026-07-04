import re

from flask_openapi3.blueprint import APIBlueprint
from pydantic import BaseModel, Field

from models.db import db
from models.user import User

auth_api = APIBlueprint("auth", __name__)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=4)
    email: str = Field(...)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    username: str = Field(...)
    password: str = Field(...)


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


@auth_api.post(
    "/register",
    summary="Register a new user",
    description="Create a new user account with username, email and password.",
)
def register(body: RegisterRequest):
    if len(body.username) < 4:
        return {"error": "Invalid username"}, 400

    if not re.match(
        r"^[A-Za-z0-9_%+-]+(\.[A-Za-z0-9_%+-]+)*@([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}$",
        body.email,
    ):
        return {"error": "Invalid email format"}, 400

    if len(body.password) < 8:
        return {"error": "Password must be at least 8 characters"}, 400
    if not re.search(r"[A-Z]", body.password):
        return {"error": "Password must contain at least one uppercase letter"}, 400
    if not re.search(r"[a-z]", body.password):
        return {"error": "Password must contain at least one lowercase letter"}, 400
    if not re.search(r"[0-9]", body.password):
        return {"error": "Password must contain at least one number"}, 400
    if not re.search(r"[!@#$%^&*_+,.?\":{}|<>-]", body.password):
        return {"error": "Password must contain at least one special character"}, 400

    if User.query.filter_by(username=body.username).first():
        return {"error": "Username is taken"}, 409
    if User.query.filter_by(email=body.email).first():
        return {"error": "Email is taken"}, 409

    user = User(body.username, body.email)
    user.set_password(body.password)

    db.session.add(user)
    db.session.commit()

    return user.to_dict(), 201


@auth_api.post(
    "/login",
    summary="Login",
    description="Authenticate a user and return a session token.",
)
def login(body: LoginRequest):
    user = User.query.filter_by(username=body.username).first()
    if not user:
        return {"error": "Invalid credentials"}, 404

    if not user.check_password(body.password):
        return {"error": "Invalid credentials"}, 404

    user.generate_session_token()
    db.session.commit()

    result = user.to_dict()
    result["token"] = user.session_token
    return result, 200


@auth_api.post(
    "/logout",
    summary="Logout",
    description="Invalidate the current session token.",
)
def logout():
    from flask import request

    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    user = _get_user_by_token(token)
    if user:
        user.clear_session_token()
        db.session.commit()
    return {"message": "Logged out"}, 200
