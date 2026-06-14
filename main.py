from flask import Flask
from flask_cors import CORS

from models.db import db
from routes.auth import auth_blueprint
from routes.vault import vault_blueprint

__all__ = ["create_app"]


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vault.db"

    CORS(app)
    db.init_app(app)

    @app.route("/")
    def root() -> str:
        return "Hello World"

    app.register_blueprint(auth_blueprint, url_prefix="/api/auth")
    app.register_blueprint(vault_blueprint, url_prefix="/api/vault")

    with app.app_context():
        db.create_all()

    return app
