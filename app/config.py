import os
from datetime import timedelta
def _as_bool(value) -> bool:
    return str(value).lower() in ('true', '1', 'yes', 't', 'y')

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("POSTGRES_DB")
    db_host = os.getenv("POSTGRES_HOST")
    db_port = os.getenv("POSTGRES_PORT")

    SQLALCHEMY_DATABASE_URI= f'postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER=os.getenv("MAIL_SERVER")
    MAIL_PORT=os.getenv("MAIL_PORT")
    MAIL_USE_TLS=_as_bool(os.getenv("MAIL_USE_TLS"))
    MAIL_USE_SSL=_as_bool(os.getenv("MAIL_USE_SSL"))
    MAIL_USERNAME=os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER")

    JWT_SECRET_KEY = os.getenv("SECRET_KEY")

    JWT_ACCESS_TOKEN_EXPIRES = (int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES")))  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = (int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES")))  # 1 day
    JWT_TOKEN_LOCATION = os.getenv("JWT_TOKEN_LOCATION")
    JWT_HEADER_TYPE = os.getenv("JWT_HEADER_TYPE")
    JWT_HEADER_NAME = os.getenv("JWT_HEADER_NAME")

    SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE")
    SCHEDULER_HOUR = (os.getenv("SCHEDULER_HOUR"))
    SCHEDULER_MINUTE = (os.getenv("SCHEDULER_MINUTE"))
    run_once_on_boot = _as_bool(os.getenv("SCHEDULER_RUN_ON_BOOT"))

    PASSWORD_RESET_SECRET =os.getenv("PASSWORD_RESET_SECRET")
    PASSWORD_RESET_SALT = os.getenv("PASSWORD_RESET_SALT")