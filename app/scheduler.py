# app/scheduler.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import SchedulerNotRunningError
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import os
from .services.token_service import cleanup_tokens
from zoneinfo import ZoneInfo
from .config import Config
from .extensions import db

def _do_global_join_status_reset(app) -> int:
    from .models import User
    with app.app_context():
        updated = (
            db.session.query(User)
                .filter(User.join_status != "not_joined")
                .update({User.join_status: "not_joined"}, synchronize_session = False)
        )
        db.session.commit()
        app.logger.warning("not joined for %s users (quiz_id=%s)", updated)
        return updated

def _reset_all_users_join_status(app, quiz_id:int) -> None:
    from .models import User, Quiz
    with app.app_context():
        q = db.session.get(Quiz, quiz_id)
        
        if not q:
            app.logger.warning("Quiz %s not found; skipping scheduled reset", quiz_id)
            return
        now = datetime.now(timezone.utc)
        if q.closes_at is not None and q.closes_at <= now:
            _do_global_join_status_reset(app)
        else:
            app.logger.warning("Scheduled reset skiped: quiz %s not yet closed.", quiz_id)

def schedule_quiz_close_reset(
        scheduler: BackgroundScheduler, app, quiz_id:int, closes_at
) -> None:
    if closes_at.tzinfo is None:
        closes_at = closes_at.replace(tzinfo = ZoneInfo(Config.SCHEDULER_TIMEZONE))

    job_id = f"reset-join-status-{quiz_id}"

    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    scheduler.add_job(
        func = _reset_all_users_join_status,
        trigger = DateTrigger(run_date = closes_at),
        args = [app, quiz_id],
        id = job_id,
        replace_existing = True,
        coalesce = False,
        misfire_grace_time = None,
    )

def reset_join_status_now(app, scheduler: BackgroundScheduler, quiz_id: int) -> None:
    job_id = f"reset-join-status-{quiz_id}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    _do_global_join_status_reset(app)
    
def start_scheduler(app) -> None:

    scheduler = BackgroundScheduler(
        timezone=ZoneInfo(Config.SCHEDULER_TIMEZONE),
    )

    def job():
        with app.app_context():
            cleanup_tokens()

    # Daily job
    scheduler.add_job(
        job,
        CronTrigger(hour=Config.SCHEDULER_HOUR, minute=Config.SCHEDULER_MINUTE, timezone = Config.SCHEDULER_TIMEZONE),
        id="cleanup-daily",
        replace_existing=True,
    )

    scheduler.start()
    import atexit
    def _shutdown():
        if scheduler.running:
            try:
                scheduler.shutdown(wait=False)
            except SchedulerNotRunningError:
                pass
    atexit.register(_shutdown)
    return scheduler