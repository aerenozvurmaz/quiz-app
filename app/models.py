from .extensions import db
from datetime import datetime, timezone, date
from sqlalchemy.dialects.postgresql import JSONB

JoinStatusEnum = db.Enum("not_joined","joined","submitted", name = "join_status", create_type=False)
UserStatusEnum = db.Enum("normal", "warned", "banned", name = "user-status", create_type= False)
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    points = db.Column(db.Integer, default = 0)
    role = db.Column(db.String(20), nullable=False, server_default="user")
    join_status = db.Column(JoinStatusEnum, nullable = False, server_default="not_joined", index=True)
    user_status = db.Column(UserStatusEnum, nullable = False, server_default="normal", index=True)
    #current_quiz_id may implemented but since there is only one quiz per week i dont think its necessary
    timeout = db.Column(db.Boolean, nullable = False, server_default = "false", index=True)
    timeout_until = db.Column(db.DateTime(timezone=True), nullable= True, index=True)
    @property
    def is_admin(self):
        return self.role == "admin"

class RefreshToken(db.Model):
    __tablename__ = 'refresh_tokens'
    jti = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True, nullable=False)
    token_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    revoked_at = db.Column(db.DateTime(timezone=True))
    device = db.Column(db.String(255))

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key = True)
    week_start_date = db.Column(db.Date, nullable=False, unique=True, index=True)
    title = db.Column(db.String(255), nullable = False)
    opens_at = db.Column(db.DateTime(timezone=True), nullable = False, index=True)
    closes_at = db.Column(db.DateTime(timezone=True), nullable = False, index=True)
    published_at = db.Column(db.DateTime(timezone=True))

    questions = db.relationship(
        "QuizQuestion",
        back_populates='quiz',
        order_by='QuizQuestion.order',
        cascade='all,delete-orphan',
        lazy="selectin",
    )

    __table_args__ = (
        db.CheckConstraint("opens_at < closes_at", name = "ck_quiz_time_window"), #db change prevent
    )

CategoryEnum = db.Enum("science", "history", "sport", "geography", "art", name = "category")
DifficultyEnum = db.Enum("easy","medium","hard", name = "difficulty")
class QuizQuestion(db.Model):
    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id", ondelete="CASCADE"), index=True, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    category = db.Column(CategoryEnum, nullable = False, server_default = "science", index=True)
    points = db.Column(db.Integer, nullable=False, default=5)
    difficulty = db.Column(DifficultyEnum, nullable=False, server_default="easy", index=True)
    quiz = db.relationship("Quiz", back_populates="questions")

    options = db.relationship(
        "QuizOption",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        db.UniqueConstraint("quiz_id", "order", name="uq_question_order_per_quiz"),
    )

class QuizOption(db.Model):
    __tablename__ = "quiz_options"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("quiz_questions.id", ondelete="CASCADE"), index=True, nullable=False)
    text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False,default=False)

    question = db.relationship("QuizQuestion", back_populates="options")

class QuizSubmission(db.Model):
    __tablename__ = "quiz_submission"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    submitted_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    action_time = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    user_status = db.Column(UserStatusEnum, nullable=True, index=True)
    answers = db.Column(JSONB, nullable=False,server_default=db.text("'{}'::jsonb"))
    score = db.Column(db.Integer, nullable = False, server_default="0")

    quiz = db.relationship("Quiz")
    user = db.relationship("User")
    __table_args__ = (
        db.UniqueConstraint("quiz_id", "user_id", name = "uq_one_submission_per_quiz"),
    )