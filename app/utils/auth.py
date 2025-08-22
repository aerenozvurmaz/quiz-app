from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def admin_required(fn):
    @wraps(fn) #decorator, dont repeat same if.. retur.. every time
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if not get_jwt().get("is_admin"):
            return jsonify(error="Admins only"), 403
        return fn(*args, **kwargs)
    return wrapper