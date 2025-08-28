from flask import Blueprint, request, jsonify, current_app
from flask_mail import Message
from itsdangerous import BadSignature, SignatureExpired

from app.services.token_service import revoke_all_for_user
from app.utils.schema_decorators import use_schema
from werkzeug.security import generate_password_hash, check_password_hash
import random
from ...extensions import db, mail, redis_client
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

    if user:
        digit_code = f"{random.randint(0,999999):06d}"
        code_key = f"pwdreset:{user.email.lower()}:code"
        attm_key = f"pwdreset:{user.email.lower()}:attempts"
        redis_client.setex(code_key, RESET_TTL_SECONDS, digit_code)
        redis_client.delete(attm_key) 

        try:

            msg = Message('Password Reset Request', recipients=[email])
            msg.body = f"Use this 6 digit code within 1 hour to reset your password:\n\n{digit_code}\n"
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {e}")        
        if current_app.config.get('ENV') != "production":
            return jsonify(msg='Email was sent for reset password', digit_code=digit_code), 200
        
    return jsonify(msg='Password reset token sent!'), 200

@bp.post('/reset_password',)
@use_schema(ResetPasswordSchema, arg_name="payload")
def api_reset_password(payload):
    email = payload["email"].strip().lower()
    digit_code = payload["digit_code"].strip()
    new_password = payload["new_password"]
    new_password_again = payload["new_password_again"]
    user = User.query.filter_by(email=email).first()

    if not new_password == new_password_again:
        return jsonify(error="Passwords not match")
    
    code_key = f"pwdreset:{user.email.lower()}:code"
    attm_key = f"pwdreset:{user.email.lower()}:attempts"
    code = redis_client.get(code_key)
    if code is None:
        return jsonify(error= "Code has expired'"), 400
    
    attempts = redis_client.incr(attm_key)

    if attempts == 1:
        ttl = redis_client.ttl(code_key)
        if ttl and ttl > 0:
            redis_client.expire(attm_key, ttl)
    if attempts > 5:
        return jsonify(error='Too many attempts. Request a new code.'), 429

    if not check_password_hash(code, digit_code):
        return jsonify(error='Invalid Codex!'), 400

    if not user:
        return jsonify(error='Invalid code!'), 400

    try:
        user.password = hash_password(new_password)
        revoke_all_for_user(user.id)
        db.session.commit()

        redis_client.delete(code_key)
        redis_client.delete(attm_key)

        return MessageSchema().dump({"msg": "Password has been reset successfully!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error="Password reset failed"), 500
