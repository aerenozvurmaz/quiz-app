from sqlalchemy import select, func
from ..extensions import db
from ..models import QuizSubmission

class SubmissionRepo:
    def get_for_user(self, quiz_id: int, user_id: int):
        return (db.session.query(QuizSubmission)
                .filter(QuizSubmission.quiz_id == quiz_id,
                        QuizSubmission.user_id == user_id)
                .first())
    
    def add_draft(self, quiz_id:int, user_id:int) -> QuizSubmission:
        sub = QuizSubmission(quiz_id=quiz_id, user_id=user_id, answers={}, score=0, submitted_at = None)
        
        db.session.add(sub)
        db.session.flush()
        return sub
    
    def update_score(self, sub:QuizSubmission, score:int):
        sub.score = score

    def submit_quiz(self, sub: QuizSubmission, when, score: int):
        sub.submitted_at = when
        sub.score = score

    def set_answers(self, sub: QuizSubmission, answers_dict: dict[int,int])->None:
        sub.answers = answers_dict

    def set_action_snapshot(self, sub: QuizSubmission, *, action_time, user_status: str)-> None:
        sub.action_time = action_time
        sub.user_status = user_status

    def count_submitted_quiz(self, quiz_id: int) -> int:
        return db.session.query(func.count(QuizSubmission.user_id)).filter(QuizSubmission.quiz_id == quiz_id,
                                                                           QuizSubmission.submitted_at.isnot(None)
                                                                           ).scalar() or 0
