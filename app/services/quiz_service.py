from __future__ import annotations
from calendar import weekday
from datetime import datetime, date, timedelta, timezone
from typing import Iterable
from psycopg2 import IntegrityError
from sqlalchemy import String, select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.quiz import QuestionPublicSchema
from app.services.token_service import delete_all_for_user, revoke_all_for_user
from ..extensions import db
from ..models import Quiz, QuizQuestion, QuizOption, QuizSubmission, User
from ..repos.quiz_repo import QuizRepo
from ..repos.submission_repo import SubmissionRepo
from ..repos.user_repo import UserRepo

quiz_repo = QuizRepo()
submission_repo = SubmissionRepo()
user_repo = UserRepo()

POINTS_BY_DIFF = {"easy": 5, "medium": 10, "hard":20}
CATEGORIES = {"science", "art", "history", "sport"}

def week_monday(d:date)->date:
    return d - timedelta(days=d.weekday())

def get_quiz_by_week(week_start:date)-> Quiz | None:
    return quiz_repo.get_by_week_start(week_monday(week_start))

def get_active_quiz(now: datetime | None = None) -> Quiz | None:
    now = now or datetime.now(timezone.utc)
    return quiz_repo.get_active_with_questions(now)

def create_quiz(
    *, title: str, opens_at: datetime, closes_at: datetime,
    week_start: date
) -> Quiz:
    week_start = week_monday(week_start)
    if opens_at >= closes_at:
        raise ValueError("opens_at must be before closes_at")
    if get_quiz_by_week(week_start):
        raise ValueError("There is already a quiz for this week")
    
    quiz = Quiz(
        title = title,
        opens_at = opens_at,
        closes_at = closes_at,
        week_start_date = week_start,
    )

    return quiz_repo.add_quiz(quiz)

def add_questions(quiz_id:int, questions: list[dict])->None: #rollback ekle
    order = 1 
    for q in questions:
        difficulty = q.get("difficulty")
        points = POINTS_BY_DIFF.get(difficulty,5)
        qq = QuizQuestion(
            quiz_id = quiz_id,
            order = order,
            text = q["text"],
            category = q.get("category"),
            difficulty = q.get("difficulty"),
            points = int(points),
        )
        qq = quiz_repo.add_question(qq)
        for opt in q.get("options",[]):
            quiz_repo.add_option(QuizOption(
                question_id = qq.id,
                text = opt["text"],
                is_correct = bool(opt.get("is_correct", False)),
            ))
        order += 1

def publish_quiz(quiz_id:int, when: datetime | None = None) -> None:
    quiz = quiz_repo.get_by_id(quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    quiz_repo.set_published_at(quiz, when or func.now())

def finish_quiz(quiz_id:int, when: datetime | None = None) -> None:

    quiz = quiz_repo.get_by_id(quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    now = datetime.now(timezone.utc)
    if now < quiz.opens_at:
        raise ValueError("Quiz not started yet")
    if now > quiz.closes_at:
        raise ValueError("Quiz already finished")
    quiz_repo.set_closes_at(quiz, when or func.now())

def score_answers(quiz: Quiz, answers: dict[int, int]) -> int:
    total = 0
    answers = {int(k): int(v) for k,v in (answers or {}).items()}
    correct_map = {q.id: {o.id for o in q.options if o.is_correct} for q in quiz.questions}
    points_by_qid = {q.id: int(POINTS_BY_DIFF.get(q.difficulty, q.points or 0)) for q in quiz.questions}
    
    for qid, oid in answers.items():
        if qid in correct_map and oid in correct_map[qid]:
            total += points_by_qid.get(qid,0)
    return total

def submit_quiz(*, quiz_id: int, user_id: int) -> QuizSubmission:
    user = user_repo.get_user_by_id(user_id)

    if not user:
        raise ValueError("User not found")
    if user.timeout:
        raise ValueError("user has a timeout for quizzes. timeout until", user.timeout_until)
    if user.user_status == "banned":
        raise ValueError("user banned from this application")
    if not user.join_status == "joined":
        raise ValueError("User not joined or already submit this quiz")

    quiz = quiz_repo.get_with_question(quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    now = datetime.now(timezone.utc)

    if not(quiz.published_at and quiz.opens_at <= now <= quiz.closes_at):
        raise ValueError("Quiz not opened yet")
    
    sub = submission_repo.get_for_user(quiz_id, user_id)
    if sub and sub.submitted_at:
        raise ValueError("Already submitted")
    if not sub:
        sub = submission_repo.add_draft(quiz_id,user_id)
    
    answers_norm = {int(k): int(v) for k, v in (sub.answers or {}).items()}

    sub.answers = answers_norm
    final_score = score_answers(quiz, sub.answers or {})
    day_bonus = 6 - datetime.now().weekday()
    total = final_score + day_bonus

    submission_repo.submit_quiz(sub, func.now(), total)
    user_repo.add_points(user_id, total)
    user_repo.update_join_status(user, "submitted")
    return sub

def join_quiz(user_id:int, quiz_id:int):
    user = user_repo.get_user_by_id(user_id)
    if not user:
        raise ValueError ("User not found")
    if user.join_status == "submitted":
        raise ValueError("user already submitted this quiz")
    if user.user_status == "warned":
        raise ValueError("user has a timeout for quizzes. timeout until", user.timeout_until)
    if user.user_status == "banned":
        raise ValueError("user banned from this application")
    quiz = quiz_repo.get_by_id(quiz_id)
    if not quiz.published_at:
        raise ValueError("Quiz not opened yet")
    user_repo.update_join_status(user, "joined")

def edit_quiz(quiz_id: int, question_id: int, data:dict) -> QuizQuestion:
    quiz = quiz_repo.get_by_id(quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    
    if datetime.now(timezone.utc) >= quiz.opens_at:
        raise ValueError("Quiz started no chance to edit")
    
    qq = (QuizQuestion.query
          .options(selectinload(QuizQuestion.options))
          .filter_by(id=question_id, quiz_id=quiz_id)
          .first())
    if not qq:
        raise ValueError("Question not found")
    
    if "text" in data: qq.text = data["text"]
    if "difficulty" in data: 
        if data["difficulty"] not in("easy", "medium","hard"):
            raise ValueError("Difficulty must be easy, medium, or hard")
        qq.difficulty = data["difficulty"]
    if "points" in data: 
        if data["points"] not in(5, 10, 20):
            raise ValueError("Points must be 5, 10, or 20")
        qq.points = int(data["points"])
    if "category" in data: 
        if data["category"] not in ("science","art", "history", "sport","art"):
            raise ValueError("Invalid category")
        qq.category = data["category"]
    if "order" in data: qq.order = data["order"]

    if "options" in data:
        options_payload = data["options"] or []
        for o in list(qq.options):
            db.session.delete(o)
        for op in options_payload:
            if "text" not in op:
                raise ValueError("each option needs 'text'")
            quiz_repo.add_option(QuizOption(
                question_id=qq.id,
                text=op["text"],
                is_correct=bool(op.get("is_correct",False))
            ))

    return qq
     


def add_question(quiz_id: int, data:dict) -> QuizQuestion:
    quiz = quiz_repo.get_by_id( quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    
    if datetime.now(timezone.utc) >= quiz.opens_at:
        raise ValueError("Quiz started no chance to edit")
    
    if "text" in data: text = data["text"]
    if "difficulty" in data: 
        if data["difficulty"] not in("easy", "medium","hard"):
            raise ValueError("Difficulty must be easy, medium, or hard")
        difficulty = data["difficulty"]
    if "points" in data: 
        if data["points"] not in(5, 10, 20):
            raise ValueError("Points must be 5, 10, or 20")
        points = int(data.get("points", POINTS_BY_DIFF.get(difficulty,5)))
    if "category" in data: 
        if data["category"] not in ("science","art", "history", "sport","art"):
            raise ValueError("Invalid category")
        category = data["category"]

    max_order = quiz_repo.max_question_order(quiz_id)
    
    new_order = (data.get("order", max_order+1))
    try:
        qq = QuizQuestion(
                quiz_id = quiz_id,
                order = new_order,
                text = text,
                category = category,
                difficulty = difficulty,
                points = points,
            )
        qq = quiz_repo.add_question(qq)

        for op in (data.get("options") or []):
            if "text" not in op:
                raise ValueError("each option needs text")
            quiz_repo.add_option(QuizOption(question_id=qq.id,text= op["text"],is_correct=bool(op.get("is_correct", False))))

        return qq

    except(ValueError, IntegrityError, SQLAlchemyError):
        db.session.rollback()
        raise

def save_answer(*, quiz_id: int, user_id: int, question_id:int, option_id:int) -> QuizSubmission:
    user = user_repo.get_user_by_id(user_id)
    if not user.join_status == "joined":
        raise ValueError("User not joined on this quiz")
    if user.join_status == "submitted":
        raise ValueError("User already submitted this quiz")
    quiz = quiz_repo.get_with_question(quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    now = datetime.now(timezone.utc)

    if not(quiz.published_at and quiz.opens_at <= now <= quiz.closes_at):
        raise ValueError("Quiz not opened yet")
    
    
    if not quiz_repo.question_exists(quiz_id, question_id):
        raise ValueError("Question not found")
    
    
    if not quiz_repo.option_belongs(option_id, question_id):
        raise ValueError("Option does not belong to this question")
    
    sub = submission_repo.get_for_user(quiz_id, user_id)
    
    if sub and sub.submitted_at:
        raise ValueError("Already submitted, cannot change answers")
    if not sub:
        sub = submission_repo.add_draft(quiz_id, user_id)

    answers = {int(k):int(v) for k, v in (sub.answers or {}).items()}
    answers[int(question_id)] = int(option_id)
    sub.answers = answers

    points_map = {q.id: q.points for q in quiz.questions}
    correct_map = {q.id: {o.id for o in q.options if o.is_correct} for q in quiz.questions}
    partial = sum(points_map[qid] for qid, oid in answers.items() if oid in correct_map.get(qid, set()))


    return {"attempt_id": sub.id, "answered_count": len(answers), "partial_score": partial}

def get_my_answers(quiz_id: int, user_id: int, now: datetime|None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    quiz = quiz_repo.get_by_id(quiz_id)
    if not quiz:
        raise ValueError("Quiz not found")
    sub = submission_repo.get_for_user(quiz_id, user_id)

    if not sub or not sub.answers:
        raise ValueError("No answers found for this quiz")
    
    answers = {int(k): int(v) for k, v in (sub.answers or {}).items()}
    reveal = quiz.closes_at <= now

    option_map = {o.id: o for q in quiz.questions for o in q.options}
    correct_map = {q.id: {o.id for o in q.options if o.is_correct} for q in quiz.questions}
    question_map = {q.id: q for q in quiz.questions}

    items: list[dict] = []
    for qid, chosen_oid in answers.items():
        q = question_map.get(qid)
        if not q:
            continue

        chosen_opt = option_map.get(chosen_oid)
        correct_ids = correct_map.get(qid, set())

        row = {
            "question_id": q.id,
            "order": q.order,
            "text": q.text,
            "chosen_option_id": chosen_oid,
            "chosen_option_text": chosen_opt.text if chosen_opt else None,
        }

        if reveal:
            row["is_correct"] = chosen_oid in correct_ids
            row["correct_option_ids"] = list(correct_ids)
            row["correct_options"] = [
                {"id": oid, "text": option_map[oid].text} for oid in correct_ids
                if oid in option_map
            ]
            row["points"] = q.points
        items.append(row)

    result: dict = {
        "quiz_id": quiz_id,
        "title": quiz.title,
        "submitted": sub.submitted_at is not None,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        "answers": sorted(items, key=lambda x: x["order"]),
        "reveal_correctness": reveal,
    }

    if reveal and sub.submitted_at:
        result["score"] = sub.score
    return result

def can_join(user_id: int, quiz_id: int, now = None):
    now = now or datetime.now(timezone.utc)
    user = user_repo.get_user_by_id(user_id)
    quiz = quiz_repo.get_by_id(quiz_id)

    if not user or not quiz:
        raise ValueError("User or quiz not found")
    
    if user.user_status == "banned":
        raise ValueError("User is banned")
    
    if user.timeout and user.timeout_until and now >= user.timeout_until:
        user.timeout = False
        user.timeout_until = None
        
    if user.timeout:
        raise ValueError("User is in timeout for this quiz.")
    
def warn_user(user_id: int, quiz_id:int) -> None:
    now = datetime.now(timezone.utc)
    user = user_repo.get_user_by_id(user_id)
    quiz = quiz_repo.get_by_id(quiz_id)

    if not user or not quiz:
        raise ValueError("User or quiz not found")
    
    base = quiz.opens_at 
    until = base + timedelta(days=14)
    user_repo.set_warned_timeout(user,until)

    sub = submission_repo.get_for_user(quiz_id, user_id) or submission_repo.add_draft(quiz_id,user_id)
    submission_repo.set_action_snapshot(sub, action_time=datetime.now(timezone.utc), user_status="warned")

def ban_user(user_id: int, quiz_id:int) -> None:
    now = datetime.now(timezone.utc)
    user = user_repo.get_user_by_id(user_id)
    quiz = quiz_repo.get_by_id(quiz_id)

    if not user or not quiz:
        raise ValueError("User or quiz not found")
    
    delete_all_for_user(user_id)
    
    sub = submission_repo.get_for_user(quiz_id, user_id) or submission_repo.add_draft(quiz_id,user_id)
    submission_repo.set_action_snapshot(sub, action_time=datetime.now(timezone.utc), user_status="banned")

def _quiz_to_paper_admin(quiz: Quiz) -> dict:
    return {
        "id": quiz.id,
        "title":quiz.title,
        "week_start_date": quiz.week_start_date.isoformat() if quiz.week_start_date else None,
        "opens_at": quiz.opens_at.isoformat() if quiz.opens_at else None,
        "closes_at": quiz.closes_at.isoformat() if quiz.closes_at else None,
        "questions": [
            {
                "id": qq.id,
                "order": qq.order,
                "text": qq.text,
                "category": qq.category,
                "difficulty": qq.difficulty,
                "points": qq.points,
                "options":[
                    {"id": o.id, "text": o.text, "is_correct": bool(o.is_correct)}
                    for o in (qq.options or [])
                ],
            }
            for qq in (quiz.questions or [])
        ]
    }

def _quiz_to_paper_user(quiz:Quiz)->dict:
    return {
        "id": quiz.id,
        "title":quiz.title,
        "week_start_date": quiz.week_start_date.isoformat() if quiz.week_start_date else None,
        "opens_at": quiz.opens_at.isoformat() if quiz.opens_at else None,
        "closes_at": quiz.closes_at.isoformat() if quiz.closes_at else None,
        "questions": [
            {
                "id": qq.id,
                "order": qq.order,
                "text": qq.text,
                "category": qq.category,
                "options":[
                    {"id": o.id, "text": o.text}
                    for o in (qq.options or [])
                ],
            }
            for qq in (quiz.questions or [])
        ]
    }

def get_quiz_for_user(quiz_id: int)->dict:
    q = quiz_repo.get_with_question(quiz_id)
    if not q:
        raise ValueError("quiz not found")
    return _quiz_to_paper_user(q)

def get_quiz_for_admin(quiz_id: int)->dict:
    q = quiz_repo.get_with_question(quiz_id)
    if not q:
        raise ValueError("quiz not found")
    return _quiz_to_paper_admin(q)

def get_total_user_for_quiz(quiz_id:int):
    joined_users = user_repo.count_joined_current()
    submitted = user_repo.count_submitted_current(quiz_id)
    total = joined_users + submitted
    return total

def get_question_for_user(quiz_id: int, order_no: int) -> dict:
    qq = quiz_repo.get_question_by_order(quiz_id, order_no)

    if not qq:
        if not quiz_repo.get_by_id(quiz_id):
            raise ValueError("Quiz not found")
        raise ValueError("Question not found")
    
    payload = QuestionPublicSchema().dump(qq)
    max_order = quiz_repo.max_question_order(quiz_id)
    has_next = order_no < max_order

    return{
        "question": payload,
        "has_next": has_next,
        "max_order": max_order,
    }