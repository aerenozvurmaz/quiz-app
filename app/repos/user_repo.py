from datetime import datetime
from typing import Optional

from sqlalchemy import func
from ..extensions import db
from ..models import User

class UserRepo:
    def get_user_by_id(self, user_id: int)-> Optional[User]:
        return db.session.get(User, user_id)
    
    def get_user_by_username(self, username:str)-> Optional[User]:
        return db.session.query(User).filter_by(username= username).first()
    
    def update_join_status(self, user: User, status:str):
        user.join_status = status

    def exists_username(self, username:str) -> bool:
        return (db.session.query(User.id).filter_by(username=username.strip()).first()) is not None
    
    def email_banned(self, email:str) -> bool:
        return User.query.filter(User.email==email, User.user_status=="banned").first() is not None
    
    def exists_email(self, email:str) -> bool:
        return User.query.filter_by(email=email).first() is not None
    
    def add_points(self, user_id:int, delta_points: int):
        db.session.query(User).filter(User.id == user_id).update(
            {User.points: User.points + delta_points}, synchronize_session=False
        )
    def update_password_hash(self, user: User, new_hash:str):
        user.password = new_hash

    def set_warned_timeout(self, user:User, until:datetime)-> None:
        user.user_status = "warned"
        user.timeout = True
        user.timeout_until = until

    def set_banned(self, user:User) -> None:
        user.user_status = "banned"
        user.timeout = True
        user.timeout_until = None 

    def count_joined_current(self)-> int:
        return db.session.query(func.count(User.id)).filter(User.join_status == "joined").scalar() or 0

    def count_submitted_current(self, quiz_id:int)-> int:
        return db.session.query(func.count(User.id)).filter(User.join_status == "submitted").scalar() or 0
