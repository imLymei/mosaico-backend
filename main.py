from flask_cors import CORS
from flask_openapi3.models.info import Info
from flask_openapi3.openapi import OpenAPI

from models.db import db
from routes.auth import auth_api
from routes.vault import vault_api

__all__ = ["create_app"]


def create_app(database_uri: str | None = None) -> OpenAPI:
    app = OpenAPI(
        __name__,
        info=Info(
            title="Mosaico API",
            version="0.1.0",
            description="Mosaico Vault Management API",
        ),
    )
    if database_uri is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vault.db"

    CORS(app)
    db.init_app(app)

    app.validation_error_status = "400"

    @app.route("/")
    def root() -> str:
        return "Hello World"

    @app.route("/docs")
    def docs_redirect():
        from flask import redirect
        return redirect("/openapi/swagger", code=302)

    app.register_api(auth_api, url_prefix="/api/auth")
    app.register_api(vault_api, url_prefix="/api/vault")

    with app.app_context():
        db.create_all()

    return app
