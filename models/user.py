import secrets
from datetime import datetime, timedelta, timezone
from typing import override

from werkzeug.security import check_password_hash, generate_password_hash

from models.db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    session_token = db.Column(db.String(128), nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @override
    def __init__(self, username: str, email: str):
        super().__init__()
        self.username = username
        self.email = email

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def generate_session_token(self) -> str:
        self.session_token = secrets.token_urlsafe(48)
        self.token_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        return self.session_token

    def is_token_valid(self) -> bool:
        if not self.session_token or not self.token_expires_at:
            return False
        now = datetime.now(timezone.utc)
        if self.token_expires_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        return now < self.token_expires_at

    def clear_session_token(self) -> None:
        self.session_token = None
        self.token_expires_at = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
