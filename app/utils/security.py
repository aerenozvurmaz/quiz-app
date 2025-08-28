import bcrypt, hashlib
from flask import current_app
from app.repos.token_repo import TokenRepo
from ..extensions import jwt, redis_client

_repo = TokenRepo()

def _acc_allow(jti:str) -> str: 
    return f"acc:allow:{jti}"

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(hashed_password: str, user_password: str) -> bool:
    try:
        return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def hash_refresh_token(token: str) -> str:
    pepper = current_app.config.get('REFRESH_TOKEN_PEPPER', "")
    return hashlib.sha256((token + pepper).encode('utf-8')).hexdigest()

def init_jwt(app):
    jwt.init_app(app)

    @jwt.token_in_blocklist_loader
    def token_in_blocklist(_hdr, payload:dict) -> bool:
        token_type = payload.get("type")
        jti = payload["jti"]

        if token_type == "access":
            return not redis_client.exists(_acc_allow(jti))
        
        if token_type == "refresh":
            row = _repo.get_by_jti(jti)
            return (row is None) or (row.revoked_at is not None)
        
        return True