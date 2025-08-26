from flask import Blueprint, jsonify, request, current_app
from app.services.leaderboard_service import list_past_quizzes_with_my_placement
from app.utils.schema_decorators import use_schema
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import selectinload
from ...models import Quiz, QuizQuestion
from ...services.quiz_service import (
    add_question, ban_user, create_quiz, add_questions, delete_question, edit_quiz, get_my_answers, get_question_for_user, get_total_user_for_quiz, publish_quiz, finish_quiz,
    join_quiz, save_answer, submit_quiz, get_active_quiz, warn_user, get_quiz_for_admin, get_quiz_for_user
)
from ...schemas.quiz import AnswerSchema, QuizCreateSchema, QuizPaperPublicSchema, QuizPaperSchema, QuestionSchema
from ...utils.auth import admin_required
from ...utils.responses import success, fail
from ...extensions import db
from app.scheduler import reset_join_status_now, schedule_quiz_close_reset, start_scheduler
from apscheduler.schedulers.background import BackgroundScheduler



bp = Blueprint("quiz", __name__, url_prefix="/api/v1/quiz")

@bp.get("")
def api_active_quiz():
    q = get_active_quiz()
    if not q:
        return success({"active": False})
    data = QuizPaperPublicSchema().dump(q)
    total = get_total_user_for_quiz(q.id)
    return success({"active":True, "quiz": data, "total participants": total})

@bp.post("create")
@admin_required
@use_schema(QuizCreateSchema, arg_name="payload")
def api_create_quiz(payload):
    from sqlalchemy.exc import SQLAlchemyError
    from apscheduler.schedulers.base import SchedulerNotRunningError
    from datetime import timezone

    try:
        quiz = create_quiz(
            title=payload["title"],
            week_start=payload["week_start_date"],
            opens_at=payload["opens_at"],
            closes_at=payload["closes_at"],
        )

        db.session.flush()

        add_questions(quiz.id, payload["questions"])
        db.session.commit()

    except (ValueError, SQLAlchemyError) as e:
        db.session.rollback()
        return fail(e, 400)

    app = current_app._get_current_object()
    aps = app.extensions.get("scheduler")

    closes_at = quiz.closes_at

    closes_at = closes_at.astimezone(timezone.utc)

    schedule_quiz_close_reset(aps, app, quiz.id, closes_at)

    return success({"quiz_id": quiz.id}, 201)


@bp.post("/<int:quiz_id>/publish")
@admin_required
def api_publish_quiz(quiz_id:int):
    try:
        publish_quiz(quiz_id)
        db.session.commit()
        return success()
    except ValueError as e:
        db.session.rollback()
        return fail(e,400)
    
@bp.post("/<int:quiz_id>/finish")
@admin_required
def api_finish_quiz(quiz_id:int):
    try:
        finish_quiz(quiz_id)
        db.session.commit()
        scheduler = current_app.extensions["scheduler"]
        reset_join_status_now(current_app, scheduler, quiz_id)
        return success()
    except ValueError as e:
        db.session.rollback()
        return fail(e, 400)
    
@bp.post("/<int:quiz_id>/join")
@jwt_required()
def api_join_quiz(quiz_id:int):
    user_id = get_jwt_identity()
    try:
        join_quiz(user_id=user_id, quiz_id=quiz_id)
        db.session.commit()
        return success()
    except ValueError as e:
        db.session.rollback()
        return fail(e, 400)

@bp.post("/<int:quiz_id>/submit")
@jwt_required()
def api_submit_quiz(quiz_id:int):
    user_id = int(get_jwt_identity())
    
    try:
        submit = submit_quiz(quiz_id=quiz_id, user_id=user_id)
        db.session.commit()
        return success({"submission_id": submit.id, "score": submit.score}, 201)

    except ValueError as e:
        db.session.rollback()
        return fail(e ,400)
    


@bp.post("/<int:quiz_id>/answers/<int:question_id>")
@jwt_required()
@use_schema(AnswerSchema, arg_name="payload")
def api_save_answer(quiz_id:int, question_id:int, payload):
    user_id = int(get_jwt_identity())
    try:
        option_id = int(payload["option_id"])
    except Exception:
        return fail("option_id is required and must be inteeger",400)
    try:
        result = save_answer(quiz_id=quiz_id, user_id=user_id,
                             question_id=question_id, option_id=option_id)
        db.session.commit()
        return success(result)
    except ValueError as e:
        db.session.rollback()
        return fail(e, 400)

    
@bp.get("/<int:quiz_id>/paper")
def api_quiz_paper(quiz_id: int):
    q = get_quiz_for_user(quiz_id)
    if not q:
        return fail("Quiz not found", 404)
    return success(q)

@bp.get("/<int:quiz_id>/paper_admin")
@admin_required
def api_quiz_paper_admin(quiz_id: int):
    q = get_quiz_for_user(quiz_id)
    if not q:
        return fail("Quiz not found", 404)
    return success(q)


@bp.put("/<int:quiz_id>/questions/<int:question_id>")
@admin_required
@use_schema(QuestionSchema, arg_name="payload", load_kwargs={"partial": True})
def api_edit_quiz(quiz_id:int, question_id:int, payload):
    try:
        qq = edit_quiz(quiz_id, question_id, payload)
        db.session.commit()
        return success(QuestionSchema().dump(qq))
    except ValueError as e:
        db.session.rollback()
        return fail(e, 400)

@bp.post("/<int:quiz_id>/questions")
@admin_required
@use_schema(QuestionSchema, arg_name="payload")
def api_add_question(quiz_id:int, payload):
    try: 
        qq = add_question(quiz_id, payload)
        db.session.commit()
        return success(QuestionSchema().dump(qq))
    except ValueError as e:
        db.session.rollback()
        return fail(e, 400)
    
@bp.delete("/<int:quiz_id>/questions/<int:question_id>")
@admin_required
def api_delete_question(quiz_id:int, question_id:int):
    try:
        qq = delete_question(quiz_id, question_id)
        db.session.commit()
        return success()
    except ValueError as e:
        db.session.rollback()
        return fail(e,400)

@bp.get("/past")
@jwt_required(optional=True)
def api_list_past_quizzes():
    user_id = get_jwt_identity()
    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))

    except Exception:
        return jsonify(error="limit/offset must be integers"), 400

    data = list_past_quizzes_with_my_placement(
        user_id=int(user_id) if user_id is not None else None,
        limit=limit,
        offset=offset
    )
    return jsonify(data), 200

@bp.get("/<int:quiz_id>/my-answers")
@jwt_required()
def api_my_answers(quiz_id:int):
    user_id = get_jwt_identity()
    try:
        data = get_my_answers(quiz_id=quiz_id, user_id=user_id)
        return success(data)
    except ValueError as e:
        return fail(str(e),404)
    

@bp.post("/<int:quiz_id>/warn/<int:user_id>")
@admin_required
def api_warn_user(quiz_id:int, user_id: int):
    try:
        warn_user(user_id=user_id, quiz_id=quiz_id)
        db.session.commit()
        return success({"status": "warned"})
    except ValueError as e:
        db.session.rollback()
        return fail(e,400)
    
@bp.post("/<int:quiz_id>/ban/<int:user_id>")
@admin_required
def api_ban_user(quiz_id:int, user_id: int):
    try:
        ban_user(user_id=user_id, quiz_id=quiz_id)
        db.session.commit()
        return success({"status": "banned"})
    except ValueError as e:
        db.session.rollback()
        return fail(e,400)

@bp.get("<int:quiz_id>/questions/<int:order_no>")
def api_get_question_by_order(quiz_id: int, order_no: int):
    try: 
        data = get_question_for_user(quiz_id, order_no)
        return success(data)
    except ValueError as e:
        return fail(str(e), 404)