from typing import Sequence, Tuple
from sqlalchemy import and_, exists, func, not_
from sqlalchemy.orm import aliased
from ..extensions import db
from ..models import Quiz, QuizSubmission, User

class LeaderboardRepo:
    @staticmethod
    def rank_window():
        return func.dense_rank().over(
        partition_by=QuizSubmission.quiz_id,
        order_by=(QuizSubmission.score.desc(), QuizSubmission.submitted_at.asc()),
    )

    @staticmethod
    def _is_user_currently_banned():
        return and_(User.timeout.is_(True), User.timeout_until.is_(None))
    
    @staticmethod
    def _not_flagged_for_quiz(quiz_id: int, user_id: int) -> bool:
        submission2 = aliased(QuizSubmission)
        flagged = exists().where(and_(
            submission2.quiz_id == quiz_id,
            submission2.user_id == user_id,
            submission2.submitted_at.isnot(None),
            submission2.user_status.in_(("warned", "banned")),
        ))
        return not_(flagged)
    
    @staticmethod
    def _all_time_rank_window():
        return func.dense_rank().over(order_by=(User.points.desc(), User.created_at.asc()))
    
    def all_time_rows(self, limit: int, offset: int):
        rank = self._all_time_rank_window()
        rows = (
            db.session.query(
                User.id.label("user_id"),
                User.username.label("username"),
                User.points.label("points"),
                rank.label("rank"),
            )
            .filter(User.points > 0)
            .order_by(User.points.desc(), User.created_at.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        total = db.session.query(func.count(User.id).filter(User.points > 0)).scalar() or 0
        return rows, total
    
    def all_time_current_user_row(self, user_id: int):
        rank = self._all_time_rank_window()
        return (
            db.session.query(
                User.id.label("user_id"),
                User.username.label("username"),
                User.points.label("points"),
                rank.label("rank"),
            )
        
            .filter(User.id == user_id)
            .one_or_none()
        )
    

    def quiz_leaderboard_rows(self, quiz_id: int, limit: int, offset:int) -> Tuple[Sequence,int]:
        rank = self.rank_window()
        not_flagged = self._not_flagged_for_quiz(QuizSubmission.quiz_id, QuizSubmission.user_id)
        not_banned_now = not_(self._is_user_currently_banned())

        rows = (
            db.session.query(
            QuizSubmission.quiz_id.label("quiz_id"),
            QuizSubmission.user_id.label("user_id"),
            User.username.label("username"),
            QuizSubmission.score.label("score"),
            QuizSubmission.submitted_at.label("submitted_at"),
            rank.label("rank"),
            )
            .join(User, User.id == QuizSubmission.user_id)
            .filter(
                QuizSubmission.quiz_id == quiz_id,
                QuizSubmission.submitted_at.isnot(None),
                not_flagged,
                not_banned_now
            )
            .order_by(QuizSubmission.score.desc(),QuizSubmission.submitted_at.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        total = (
            db.session.query(func.count(QuizSubmission.user_id))
            .filter(
                QuizSubmission.quiz_id == quiz_id,
                QuizSubmission.submitted_at.isnot(None),
                not_flagged,
                not_banned_now,
            )
            .scalar() or 0
        )

        return rows, total
    
    def quiz_current_user_row(self, quiz_id: int, user_id: int):
        rank = self.rank_window()
        not_flagged = self._not_flagged_for_quiz(quiz_id, QuizSubmission.user_id)
        not_banned_now = not_(self._is_user_currently_banned())
        return(
            db.session.query(
                QuizSubmission.user_id.label("user_id"),
                User.username.label("username"),
                QuizSubmission.score.label("score"),
                QuizSubmission.submitted_at.label("submitted_at"),
                rank.label("rank"),
            )
            .join(User, User.id == QuizSubmission.user_id)
            .filter(
                QuizSubmission.quiz_id == quiz_id,
                QuizSubmission.user_id == user_id,
                QuizSubmission.submitted_at.isnot(None),
                not_flagged,
                not_banned_now,
            )
            .first()
        )
    
    def past_quizzes_with_my_placement(
            self, user_id: int, limit: int, offset: int) -> Tuple[Sequence,int]:
        now = func.now()
        not_banned_now = not_(self._is_user_currently_banned())
        participants_sq = (
            db.session.query(func.count(QuizSubmission.user_id))
            .filter(
                QuizSubmission.quiz_id == Quiz.id,
                QuizSubmission.submitted_at.isnot(None),
            )
            .correlate(Quiz)
        )
        if user_id is not None:
            flagged = self._not_flagged_for_quiz(QuizSubmission.quiz_id, QuizSubmission.user_id)
            my_rank_sub = (
                db.session.query(
                    QuizSubmission.quiz_id.label("quiz_id"),
                    QuizSubmission.user_id.label("user_id"),
                    QuizSubmission.score.label("score"),
                    QuizSubmission.submitted_at.label("submitted_at"),
                    func.dense_rank().over(
                        partition_by=QuizSubmission.quiz_id,
                        order_by=(
                            QuizSubmission.score.desc(),
                            QuizSubmission.submitted_at.asc(),
                        ),
                    ).label("rank"),
                )
                .filter(QuizSubmission.submitted_at.isnot(None),
                        flagged,
                        not_banned_now,)
                .subquery("my_rank")
            )
            rows = (
                db.session.query(
                    Quiz.id.label("quiz_id"),
                    Quiz.title,
                    Quiz.week_start_date,
                    Quiz.opens_at,
                    Quiz.closes_at,
                    my_rank_sub.c.rank.label("my_rank"),
                    my_rank_sub.c.score.label("my_score"),
                    my_rank_sub.c.submitted_at.label("my_submitted_at"),
                    participants_sq.label("participants"),
                )
                .outerjoin(
                    my_rank_sub,
                    (my_rank_sub.c.quiz_id == Quiz.id)
                    & (my_rank_sub.c.user_id == user_id)
                )
                .filter(Quiz.closes_at < now)
                .order_by(Quiz.week_start_date.desc(), Quiz.id.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
        else:
            rows = (
                db.session.query(
                    Quiz.id.label("quiz_id"),
                    Quiz.title,
                    Quiz.week_start_date,
                    Quiz.opens_at,
                    Quiz.closes_at,
                    participants_sq.label("participants"),
                )
                .filter(Quiz.closes_at < now)
                .order_by(Quiz.week_start_date.desc(), Quiz.id.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )
        total = (
            db.session.query(func.count(Quiz.id))
            .filter(Quiz.closes_at < now,
                    flagged,
                    not_banned_now,)
            .scalar()or 0
        )

        return rows, total