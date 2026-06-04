from flask import Blueprint, jsonify, request

auth_blueprint = Blueprint("auth", __name__)


@auth_blueprint.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    return jsonify({"test": "success"})
