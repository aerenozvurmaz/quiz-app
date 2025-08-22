import bcrypt, hashlib
from flask import current_app

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
