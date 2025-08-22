from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, defer
from ..extensions import db
from ..models import Quiz, QuizQuestion, QuizOption

class QuizRepo:
    def get_by_id(self, quiz_id:int):
        return db.session.get(Quiz, quiz_id)
    
    def get_with_question(self, quiz_id:int):
        return (db.session.query(Quiz)
                .options(selectinload(Quiz.questions).selectinload(QuizQuestion.options))
                .filter(Quiz.id==quiz_id)
                .first())
    
    def get_by_week_start(self, week_start_date):
        return (db.session.query(Quiz)
                .filter(Quiz.week_start_date == week_start_date)
                .first())
    
    def get_active_with_questions(self, now):
        return (db.session.query(Quiz)
                .options(selectinload(Quiz.questions)
                         .defer(QuizQuestion.difficulty)
                         .defer(QuizQuestion.points)
                         .selectinload(QuizQuestion.options)
                            .defer(QuizOption.is_correct)

                )
                .filter(Quiz.opens_at <= now, Quiz.closes_at >= now, Quiz.published_at.isnot(None))
                .first())
    
    def get_active(self,now) -> Optional[Quiz]:
        return (
            db.session.query(Quiz)
            .filter(
                Quiz.opens_at <= now,
                Quiz.closes_at >= now,
                Quiz.published_at.isnot(None)
            )
        ).first()
    def question_exists(self, quiz_id: int, question_id: int) -> bool:
        return db.session.query(QuizQuestion.id).filter(
            QuizQuestion.id == question_id, QuizQuestion.quiz_id == quiz_id).limit(1).first() is not None
    
    def option_belongs(self, option_id:int, question_id:int) -> bool:
        return db.session.query(QuizOption.id).filter(
            QuizOption.id == option_id, QuizOption.question_id == question_id
            ).limit(1).first() is not None
    
    def max_question_order(self, quiz_id: int) -> int:
        return (db.session.query(func.coalesce(func.max(QuizQuestion.order), 0))
                .filter(QuizQuestion.quiz_id == quiz_id).scalar() or 0)
    
    def list_past(self, limit:int, offset:int) -> Tuple[List[Quiz], int]:
        now = func.now()
        base = db.session.query(Quiz).filter(Quiz.closes_at < now).order_by(Quiz.closes_at.desc())
        total = base.order_by(func.count(Quiz.id)).scalar() or 0
        items = base.limit(limit).offset(offset).all()
        return items, total

    def add_quiz(self, quiz:Quiz) -> Quiz:
        db.session.add(quiz)
        db.session.flush()
        return quiz

    def add_question(self, qq: QuizQuestion) -> QuizQuestion:
        db.session.add(qq)
        db.session.flush()
        return qq
    
    def add_option(self, opt: QuizOption) -> QuizOption:
        db.session.add(opt)
        return opt
    
    def set_published_at(self, quiz:Quiz, when):
        quiz.published_at = when

    def set_closes_at(self, quiz:Quiz, when):
        quiz.closes_at = when

    def get_question_by_order(self, quiz_id: int, order_no: int):
        return (
            db.session.query(QuizQuestion)
            .options(selectinload(QuizQuestion.options))
            .filter(QuizQuestion.quiz_id == quiz_id,
                    QuizQuestion.order == order_no,)
            .first()
        )

    def get_first_question(self, quiz_id: int):
        return (
            db.session.query(QuizQuestion)
            .options(selectinload(QuizQuestion.options))
            .filter(QuizQuestion.quiz_id == quiz_id,)
            .order_by(QuizQuestion.order.asc())
            .first()
        )
    
    def get_next_question_after(self, quiz_id: int, order_no: int):
        return (
            db.session.query(QuizQuestion)
            .options(selectinload(QuizQuestion.options))
            .filter(QuizQuestion.quiz_id == quiz_id,
                    QuizQuestion.order> order_no,)
            .order_by(QuizQuestion.order.asc())
            .first()
        )