from flask import jsonify

import jwt
from pony.orm import db_session

from db import AccessToken


@db_session
def json_and_response_code(request):
    if "clientToken" not in request.json or request.json["clientToken"] is None:
        return jsonify({
            "error": "IllegalArgumentException",
            "errorMessage": "Missing clientToken."
        }), 403

    if "accessToken" not in request.json or request.json["accessToken"] is None:
        return jsonify({
            "error": "IllegalArgumentException",
            "errorMessage": "Access Token can not be null or empty."
        }), 400

    if "selectedProfile" in request.json:
        return jsonify({  # This will always be true until multiple profiles per account is implemented.
            "error": "IllegalArgumentException",
            "errorMessage": "Access token already has a profile assigned."
        }), 400

    access_token = AccessToken.from_token(request.json["accessToken"])
    if access_token is None or access_token.client_token.uuid.hex != request.json["clientToken"]:
        return jsonify({
            "error": "ForbiddenOperationException",
            "errorMessage": "Invalid token"
        }), 403

    new_access_token = AccessToken(
        client_token=access_token.client_token,
        profile=access_token.profile
    )

    access_token.delete()

    response_data = {
        "accessToken": jwt.encode(new_access_token.format(), key="").decode(),
        "clientToken": new_access_token.client_token.uuid.hex,
    }

    if new_access_token.profile:
        response_data["selectedProfile"] = {
            "id": new_access_token.profile.uuid.hex,
            "name": new_access_token.profile.name
        }

    if "requestUser" in request.json and request.json["requestUser"]:
        response_data["user"] = {
            "id": new_access_token.client_token.account.uuid.hex,
            "username": new_access_token.client_token.account.username
        }

    return jsonify(response_data), 200
