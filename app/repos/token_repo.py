from __future__ import annotations
from datetime import datetime
from typing import Optional, Union
from sqlalchemy import ClauseElement, func, or_, delete
from ..extensions import db
from ..models import RefreshToken

class TokenRepo:
    def has_active_for_user(self, user_id:int)->bool:
        return(
            db.session.query(RefreshToken.user_id)
            .filter(
                RefreshToken.user_id== user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > func.now()
            )
            .first()
            is not None
        )
    
    def get_by_jti(self, jti:str):
        return db.session.get(RefreshToken, jti)

    def upsert_refresh(
            self, *, jti: str, user_id: int, token_hash: str, expires_at: datetime, device: Optional[str]
    ) -> RefreshToken:
        row = RefreshToken(
            jti = jti,
            user_id = user_id,
            token_hash = token_hash,
            expires_at = expires_at,
            device = device,
            revoked_at = None,
        )
        db.session.merge(row) #idempotent on same jti
        db.session.flush()
        return row

    def revoke_by_jti(self, jti: str, when: Union[datetime, ClauseElement]) -> bool:
        row = db.session.get(RefreshToken,jti)
        if not row:
            return False
        row.revoked_at = when
        return True
    
    def revoke_all_for_user(self, user_id: int, when: Union[datetime, ClauseElement]) -> int:
        q = (
            db.session.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        )
        return q.update({RefreshToken.revoked_at: when}, synchronize_session=False)
    
    def delete_by_jti(self, jti:str) -> bool:
        row = db.session.get(RefreshToken,jti)
        if not row:
            return False
        db.session.delete(row)
        return True
    
    def delete_all_for_user(self, user_id: int) -> int:
        return (
            db.session.query(RefreshToken)
            .filter_by(user_id=user_id)
            .delete(synchronize_session=False)
        )
    
    def cleanup_expired_or_revoked(self):
        db.session.execute(delete(RefreshToken).where(or_(RefreshToken.expires_at <= func.now(),
                                RefreshToken.revoked_at.isnot(None))))
