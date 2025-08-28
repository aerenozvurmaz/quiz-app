from flask import Flask, jsonify
from flask_cors import CORS

from app.utils.security import init_jwt
from .config import Config
from .utils.security import init_jwt
from .extensions import db, migrate, mail, jwt
from .api.health import bp as health_bp
from .api.v1.auth import bp as auth_bp
from .api.v1.password import bp as password_bp
from .scheduler import start_scheduler
from .api.v1.quiz import bp as quiz_bp
from .api.v1.leaderboard import bp as lead_bp
from marshmallow import ValidationError


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    jwt.init_app(app)
    init_jwt(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(password_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(lead_bp)

    aps = start_scheduler(app)
    app.extensions["scheduler"] = aps
    
    @app.errorhandler(ValidationError)
    def handle_validation(err):
        return jsonify({"ok": False, "error": {"message": "Validation error", "details": err.messages}}), 400
    return app
    
