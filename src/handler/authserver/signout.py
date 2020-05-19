from json import loads, decoder
from flask import jsonify
from pony.orm import db_session

from db import AccessToken
from handler.authserver._username_password_verify import account_or_none


@db_session
def json_and_response_code(request):
    try:
        request_data = loads(request.data)
    except decoder.JSONDecodeError as e:
        return jsonify({
            "error": "JsonEOFException",
            "errorMessage": f"{e.msg}: line {e.lineno} column {e.colno} (char {e.pos})"
        }), 400
    request_keys = request_data.keys()

    if "username" not in request_keys or "password" not in request_keys:
        return jsonify({
            "error": "TooManyRequestsException",
            "errorMessage": "Invalid credentials. Invalid username or password."
        }), 429

    account = account_or_none(request_data["username"], request_data["password"])
    if account is None:
        return jsonify({
            "error": "ForbiddenOperationException",
            "errorMessage": "Invalid credentials. Invalid username or password."
        }), 403

    AccessToken.select(lambda tkn: tkn.client_token.account == account).delete()

    return "", 204
