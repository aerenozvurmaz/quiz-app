from flask import Blueprint, jsonify

bp = Blueprint('health', __name__)

@bp.get('/api/health')
def health_check():
    return jsonify({"status": "ok"}), 200