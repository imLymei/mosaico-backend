from flask import Flask
from flask_cors import CORS

from models.db import db
from routes.auth import auth_blueprint


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vault.db"

    CORS(app)
    db.init_app(app)

    @app.route("/")
    def root():
        return "Hello World"

    app.register_blueprint(auth_blueprint, url_prefix="/api/auth")

    with app.app_context():
        db.create_all()

    return app
