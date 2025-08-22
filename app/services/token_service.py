from __future__ import annotations
from hmac import compare_digest
from typing import Optional
from sqlalchemy import delete, func, or_
from ..extensions import db
from ..models import RefreshToken
from datetime import datetime, timezone
from flask_jwt_extended import create_refresh_token, decode_token
from ..utils.security import hash_refresh_token
from ..repos.token_repo import TokenRepo

token_repo = TokenRepo()

def _ensure_refresh_claims(raw_token: str) -> dict:
    claims = decode_token(raw_token)
    typ = claims.get("type") or claims.get("token_type")
    if typ != "refresh":
        raise ValueError("Provided token is not a refresh token")
    if "jti" not in claims or "exp" not in claims:
        raise ValueError("Refresh token mssing required claims")
    return claims

def _device_label(device: Optional[str]):
    return (device or "unknown")[:80]



def user_has_active_refresh_token(user_id: int)->bool:
    return token_repo.has_active_for_user(user_id)

def get_refresh_by_jti(jti:str) -> RefreshToken | None:
    return token_repo.get_by_jti(jti)

def store_refresh_token(user_id: int, raw_token:str, user_device: str |None)->RefreshToken:
    claims = _ensure_refresh_claims(raw_token)
    jti = claims["jti"]
    exp_date = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    row = token_repo.upsert_refresh(
        jti=jti,
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=exp_date,
        device=_device_label(user_device),
    )
    return row

def issue_refresh_token(user_id: int, user_device: str | None)->tuple[str,RefreshToken]:
    token = create_refresh_token(identity = user_id)
    row = store_refresh_token(user_id, token, user_device)
    return token, row

def revoke_refresh_by_jti(jti:str)->bool:
    return token_repo.revoke_by_jti(jti, when=datetime.now(timezone.utc))

def revoke_refresh_by_raw(raw_token:str, expected_user_id: Optional[int] = None) -> bool:
    claims = _ensure_refresh_claims(raw_token)
    jti = claims["jti"]
    row = token_repo.get_by_jti(jti)
    if not row:
        return False
    
    if expected_user_id is not None and row.user_id != expected_user_id:
        raise ValueError("Token does not belong to the expected user.")

    hashed = hash_refresh_token(raw_token)
    if not compare_digest(row.token_hash, hashed):
        raise ValueError("Token does not match stored hash.")

    row.revoked_at = datetime.now(timezone.utc)
    return True

def revoke_all_for_user(user_id: int) -> int:
    return token_repo.revoke_all_for_user(user_id, when= func.now())

def delete_refresh_by_jti(jti: str) -> None:
    return token_repo.delete_by_jti

def delete_all_for_user(user_id:int) -> None:
    return token_repo.delete_all_for_user(user_id)

def cleanup_tokens():
    token_repo.cleanup_expired_or_revoked()

