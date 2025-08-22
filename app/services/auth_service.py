from __future__ import annotations
from typing import Optional
from ..models import User
from ..extensions import db
from ..utils.security import check_password, hash_password
from ..repos.user_repo import UserRepo

user_repo = UserRepo()

def authenticate(username: str, password:str)->Optional[User] | None:
    user = user_repo.get_user_by_username(username)
    if not user:
        return None
    if not check_password(user.password, password):
        return None
    return user

def change_password(user_id: int, old_password: str, new_password: str, new_password_again:str) -> None:
    u = user_repo.get_user_by_id(user_id)
    if not new_password == new_password_again:
        raise ValueError("Passwords not match") 
    if not u or not check_password(u.password, old_password):
        raise ValueError("Old password is incorrect.")
    u.password = hash_password(new_password)

def is_username_taken(username:str)-> bool:
    return user_repo.exists_username(username)

def is_email_taken(email:str) -> bool:
    return user_repo.exists_email(email)

def is_email_banned(email:str)->bool:
    return user_repo.email_banned(email)

def create_user(username: str, email: str, password: str) -> User:
    
    u = User(username=username, email=email, password=hash_password(password))
    db.session.add(u)
    return u