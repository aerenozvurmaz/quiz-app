import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from redis import Redis

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
jwt = JWTManager()
redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),  # in docker-compose.yml service name
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=int(os.getenv("REDIS_DB", "0")),
    decode_responses=True  # makes get() return str instead of bytes
)