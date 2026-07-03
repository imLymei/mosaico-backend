from datetime import datetime, timezone
from typing import override

from models.db import db


class Vault(db.Model):
    __tablename__ = "vaults"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    items = db.relationship("VaultItem", back_populates="vault", cascade="all, delete-orphan")

    @override
    def __init__(self, user_id: int, name: str):
        super().__init__()
        self.user_id = user_id
        self.name = name

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "name": self.name,
            "icon": self.icon,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class VaultItem(db.Model):
    __tablename__ = "vault_items"

    id = db.Column(db.Integer, primary_key=True)
    vault_id = db.Column(db.Integer, db.ForeignKey("vaults.id"), nullable=False)
    name = db.Column(db.String(256), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    mime_type = db.Column(db.String(120), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    vault = db.relationship("Vault", back_populates="items")

    @override
    def __init__(self, vault_id: int, name: str, filename: str, mime_type: str, file_size: int):
        super().__init__()
        self.vault_id = vault_id
        self.name = name
        self.filename = filename
        self.mime_type = mime_type
        self.file_size = file_size

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "vaultId": self.vault_id,
            "name": self.name,
            "filename": self.filename,
            "mimeType": self.mime_type,
            "fileSize": self.file_size,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
