from flask import Blueprint, request, jsonify, current_app
from flask_mail import Message
from itsdangerous import BadSignature, SignatureExpired

from app.services.token_service import revoke_all_for_user
from app.utils.schema_decorators import use_schema

from ...extensions import db, mail
from ...models import User
from ...utils.security import hash_password
from ...utils.tokens import password_reset_serializer, password_reset_salt
from ...schemas.auth import ForgotPasswordSchema, ResetPasswordSchema, MessageSchema

bp = Blueprint('password', __name__, url_prefix="/api/v1/password")

RESET_TTL_SECONDS = 3600

@bp.post('/forgot_password')
@use_schema(ForgotPasswordSchema, arg_name="payload")
def api_forgot_password(payload):
    email = payload["email"].strip().lower()

    user = User.query.filter_by(email=email).first()
    token = password_reset_serializer().dumps({"id": user.id, "email": user.email}, salt=password_reset_salt())

    if user:
        try:

            msg = Message('Password Reset Request', recipients=[email])
            msg.body = f"Use this token within 1 hour to reset your password:\n\n{token}\n"
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {e}")        
        if current_app.config.get('ENV') != "production":
            return jsonify(msg='Password reset token issued', token=token), 200
        
    return jsonify(msg='Password reset token sent!'), 200

@bp.post('/reset_password',)
@use_schema(ResetPasswordSchema, arg_name="payload")
def api_reset_password(payload):
    token = payload["token"].strip()
    new_password = payload["new_password"]
    new_password_again = payload["new_password_again"]

    if not new_password == new_password_again:
        return jsonify(error="Passwords not match")
    serializer = password_reset_serializer()
    try:
        payload = serializer.loads(token, salt=password_reset_salt(), max_age=RESET_TTL_SECONDS)
    except SignatureExpired:
        return jsonify(error='Token has expired!'), 400
    except BadSignature:
        return jsonify(error='Invalid token!'), 400
    
    user = User.query.get(payload.get("id"))
    if not user or user.email != payload.get("email"):
        return jsonify(error='Invalid token!'), 400
    try:
        user.password = hash_password(new_password)
        revoke_all_for_user(user.id)
        db.session.commit()
        return MessageSchema().dump({"msg": "Password has been reset successfully!"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify(error="Password reset failed"), 500
