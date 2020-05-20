from uuid import UUID

from flask import jsonify

import jwt
from pony.orm import db_session

from db import ClientToken, Profile, AccessToken
from handler.authserver._username_password_verify import account_or_none


@db_session
def json_and_response_code(request):
    if "username" not in request.json or "password" not in request.json:
        return jsonify({
            "error": "IllegalArgumentException",
            "errorMessage": "message is marked non-null but is null"
        }), 400

    account = account_or_none(request.json["username"], request.json["password"])
    if account is None:
        return jsonify({
            "error": "ForbiddenOperationException",
            "errorMessage": "Invalid credentials. Invalid username or password."
        }), 403

    try:
        client_token_uuid = UUID(request.json["clientToken"])
    except ValueError as e:
        return jsonify({
            "error": "IllegalArgumentException",
            "errorMessage": "Invalid token."
        }), 400

    client_token: ClientToken
    if "clientToken" not in request.json:
        client_token = ClientToken(account=account)
    else:
        client_token = ClientToken.get(uuid=client_token_uuid)
        if client_token is not None and client_token.account != account:  # requested clientToken is different account's
            return jsonify({  # May be inconsistent with official API
                "error": "ForbiddenOperationException",
                "errorMessage": "Invalid credentials. Invalid username or password."
            }), 403

        elif client_token is None:  # there's no client token with requested UUID
            client_token = ClientToken(account=account, uuid=client_token_uuid)

        else:  # requested clientToken exists and owned by authorized account
            client_token.refresh()

    optional_profile = {}
    if "agent" in request.json:
        available_profiles = list(
            Profile.select(lambda p: p.agent == request.json["agent"]["name"] and p.account == account))
        if len(available_profiles) == 1:
            optional_profile = {"profile": available_profiles[0]}

    access_token = AccessToken(
        client_token=client_token,
        **optional_profile
    )

    response_data = {
        "accessToken": jwt.encode(access_token.format(), key="").decode(),
        "clientToken": client_token.uuid.hex
    }

    if "requestUser" in request.json and request.json["requestUser"]:
        response_data["user"] = {
            "username": account.username,
            "id": account.uuid.hex
        }

    if "profile" in optional_profile:
        response_data["selectedProfile"] = {
            "name": optional_profile["profile"].name,
            "id": optional_profile["profile"].uuid.hex
        }
        response_data["availableProfiles"] = [response_data["selectedProfile"]]
    else:
        response_data["availableProfiles"] = []

    for token in AccessToken \
            .select(lambda candidate: candidate.client_token.account == account and candidate != access_token):
        token.authentication_valid = False

    return jsonify(response_data), 200
