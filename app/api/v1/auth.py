import re, bcrypt
from flask import Blueprint, request, session, jsonify, current_app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity,get_jwt, decode_token
from sqlalchemy import or_, func
from datetime import datetime, timezone
from ...extensions import db, jwt
from ...models import User, RefreshToken
from ...utils.security import hash_password, check_password, hash_refresh_token
from marshmallow import ValidationError
from ...schemas.auth import RegisterSchema, LoginSchema, ChangePasswordSchema, TokensResponseSchema, MessageSchema
from ...services.token_service import (
    revoke_all_for_user, revoke_refresh_by_raw, user_has_active_refresh_token, issue_refresh_token, get_refresh_by_jti,
    delete_refresh_by_jti, delete_all_for_user
)
from ...services.auth_service import authenticate, change_password, is_email_banned, is_username_taken, is_email_taken, create_user
from ...utils.schema_decorators import use_schema


bp = Blueprint('auth', __name__, url_prefix="/api/v1/auth")

@bp.post('/register')
@use_schema(RegisterSchema, arg_name="payload")
def api_register(payload):
    username = payload['username'].strip()
    password = payload['password']
    email = payload['email'].strip().lower()
    
    try:
        if is_email_banned(email):
            return jsonify(error="Email got banned"), 400
        elif is_username_taken(username):
            return jsonify(error= "Account already exists!"),400
        elif is_email_taken(email):
            return jsonify(error = "Email already registered!"),400
        
        create_user(username=username, email=email, password=password)
        db.session.commit()
        return MessageSchema().dump({"msg": 'You have successfully registered!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(error="Registration failed."), 400
    
@bp.post('/login')
@use_schema(LoginSchema, arg_name="payload")
def api_login(payload):
    device = request.headers.get("User-Device", "unknown")
    
    user = authenticate(payload["username"].strip(), payload["password"])
    if not user:
        return jsonify(error = 'Invalid credentials. Please try again.'),401
    access = create_access_token(identity = user.id, additional_claims={"is_admin": user.is_admin}, fresh=True)

    if not user_has_active_refresh_token(user.id):
        try:
            refresh, _row = issue_refresh_token(user.id, device)
            db.session.commit()
            return TokensResponseSchema().dump({"access_token": access, "refresh_token": refresh}), 200
        except Exception:
            db.session.rollback()
            return jsonify(error= "Could not issue refresh token."), 500
    return TokensResponseSchema().dump({"access_token":access}), 200

@bp.post('/change_password')
@use_schema(ChangePasswordSchema, arg_name="payload")
@jwt_required()
def api_change_password(payload):
    uid = int(get_jwt_identity())

    try:
        change_password(uid, payload["old_password"], payload["new_password"], payload["new_password_again"])
        print("xx")
        revoke_all_for_user(uid)
        print("xx")

        db.session.commit()
        return MessageSchema().dump({"msg": "Password changed successfully!"}), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify(error=str(e)), 400
    except Exception:
        db.session.rollback()
        return jsonify(error="Password change failed"), 500
    
    

@bp.post('/logout')
@jwt_required()
def api_logout():
    user_id = int(get_jwt_identity())
    
    try:
        revoke_all_for_user(user_id)
        db.session.commit()
        return MessageSchema().dump({"msg": "Logged out successfully"}), 200
    except Exception:
        db.session.rollback()
        return jsonify(error= "logout failed"), 500

@bp.post("/token/refresh")
@jwt_required(refresh=True)
def api_refresh_token():
    claims = get_jwt()
    user_id = get_jwt_identity()
    rjti = claims["jti"]

    row = get_refresh_by_jti( rjti)
    if not row or row.user_id != user_id or (row.expires_at < datetime.now(timezone.utc)):
        return jsonify(error='Invalid or revoked refresh token!'), 401
 
    try:
        revoke_refresh_by_raw(request.headers.get("Authorization", "").replace("Bearer ", "").strip() or "", expected_user_id=user_id)

        device = request.headers.get("User-Device", "unknown")
        new_access = create_access_token(identity=user_id, fresh=False)
        new_refresh, _row = issue_refresh_token(user_id, device)
        db.session.commit()
        return TokensResponseSchema().dump({"access_token": new_access, "refresh_token": new_refresh}), 200
    except ValueError as e:
        db.session.rollback()
        return jsonify(error=str(e)), 401
    except Exception:
        db.session.rollback()
        return jsonify(error="Could not rotate refrseh token"), 500