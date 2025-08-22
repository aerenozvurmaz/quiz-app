from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def password_reset_serializer() -> URLSafeTimedSerializer:
    secret = current_app.config.get("PASSWORD_RESET_SECRET") or current_app.config["SECRET_KEY"]
    return URLSafeTimedSerializer(secret)

def password_reset_salt() -> str:
    return current_app.config.get("PASSWORD_RESET_SALT", "password-reset-salt")