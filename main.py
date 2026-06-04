from flask import Flask
from flask_cors import CORS

from routes.auth import auth_blueprint


def create_app():
    app = Flask(__name__)

    CORS(app)

    @app.route("/")
    def root():
        return "Hello World"

    app.register_blueprint(auth_blueprint, url_prefix="/api/auth")

    return app
