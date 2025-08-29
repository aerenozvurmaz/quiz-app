from __future__ import annotations
from datetime import datetime, date, timezone
from functools import wraps
from flask import Blueprint, jsonify, request
from app.services.leaderboard_service import get_all_time_leaderboard, get_quiz_leaderboard, get_week_leaderboard
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request, get_jwt
from ...models import Quiz, QuizQuestion
from sqlalchemy.orm import selectinload

bp = Blueprint("leaderboard", __name__, url_prefix="/api/v1")

@bp.get("/<int:quiz_id>/leaderboard")
@jwt_required(optional=True)
def api_quiz_leaderboard(quiz_id:int):
    user_id = get_jwt_identity()
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except Exception:
        return jsonify(error="limit/offset must be integers"), 400

    try:
        data=get_quiz_leaderboard(
            quiz_id=quiz_id,
            limit=limit,
            offset=offset,
            user_id=int(user_id)
        )
        return jsonify(data), 200
    except ValueError as e:
        return jsonify(error=str(e)), 404

@bp.get("/leaderboard/week/<week_start_date>")
@jwt_required(optional=True)
def api_week_leaderboard(week_start_date: str):
    
    user_id = get_jwt_identity()
    try:
        week_start = date.fromisoformat(week_start_date)
    except Exception:
        return jsonify(error="week_start_date must be YYYY-MM-DD"), 400
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except Exception:
        return jsonify(error="limit/offset must be integers"), 400

    try:
        data = get_week_leaderboard(
            week_start=week_start,
            limit=limit,
            offset=offset,
            user_id=int(user_id) if user_id is not None else None
        )
        return jsonify(data), 200
    except ValueError as e:
        return jsonify(error=str(e)), 404
    
@bp.get("/leaderboard/all_time")
@jwt_required(optional=True)
def api_all_time_leaderboard():
    user_id = get_jwt_identity()
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except Exception:
        return jsonify(error="linit/offset must be integers"), 400
    
    data = get_all_time_leaderboard(
        limit=limit,
        offset=offset,
        user_id=int(user_id) if user_id is not None else None
    )
    return jsonify(data), 200
