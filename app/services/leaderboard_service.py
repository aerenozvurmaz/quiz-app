from __future__ import annotations
from calendar import weekday
from datetime import datetime, date, timedelta, timezone
from typing import Iterable, Optional
from psycopg2 import IntegrityError
from sqlalchemy import String, and_, select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.quiz import QuizBriefSchema
from ..extensions import db
from ..models import Quiz, QuizQuestion, QuizOption, QuizSubmission, User
from ..services import quiz_service
from ..repos.leaderboard_repo import LeaderboardRepo

lb_repo = LeaderboardRepo()


def get_quiz_leaderboard(quiz_id: int, limit: int = 10, offset: int = 0, user_id: int | None = None):
    rows, total = lb_repo.quiz_leaderboard_rows(quiz_id,limit, offset)
    
    leaderboard=[{
        "user_id": r.user_id,
        "username": r.username,
        "score": r.score,
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        "rank": int(r.rank)
    } for r in rows]

    cur_user = None
    if user_id is not None:
        r = lb_repo.quiz_current_user_row(quiz_id, user_id)
        if r:
            cur_user = {
                "user_id": r.user_id,
                "username": r.username,
                "score": r.score,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                "rank": r.rank
            }
    return {"quiz_id": quiz_id, "leaderboard": leaderboard, "current_user": cur_user, "total": total}

def get_week_leaderboard(week_start:date, limit: int = 10, offset: int = 0, user_id: int | None = None):
    q = quiz_service.get_quiz_by_week(quiz_service.week_monday(week_start))
    if not q:
        raise ValueError("Quiz not found for that week")
    return get_quiz_leaderboard(q.id, limit=limit, offset=offset, user_id=user_id)

def list_past_quizzes_with_my_placement(
        user_id: Optional[int], limit: int = 20, offset: int = 0
):
    rows, total = lb_repo.past_quizzes_with_my_placement(user_id, limit, offset)

    items = []

    for r in rows:
        item = {
            "quiz_id": r.quiz_id,
            "title": r.title,
            "week_start_date": r.week_start_date.isoformat() if r.week_start_date else None,
            "opens_at": r.opens_at.isoformat() if r.opens_at else None,
            "closes_at": r.closes_at.isoformat() if r.closes_at else None,
            "participants": r.participants or 0
        }

        item["my"] = (
            {
                "rank": r.my_rank,
                "score": r.my_score,
                "submitted_at": r.my_submitted_at.isoformat() if r.my_submitted_at else None
            }
            if r.my_rank is not None
            else None
        )
    items.append(item)

    return{
        "limit": int(limit),
        "offset": int(offset),
        "total": total,
        "items": items,
    }
