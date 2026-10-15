from collections.abc import Generator
from datetime import UTC, date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends
from sqlalchemy.orm import Session

from common.config import settings
from common.db.session import SessionLocal
from common.gateway.job_queue_celery import CeleryJobQueue
from common.gateway.protocol import JobQueue
from common.local_date import to_local_date
from features.exercise.protocol import ExerciseRepository
from features.exercise.repository import DbExerciseRepository
from features.program.protocol import ProgramRepository, ProgramRulesRepository
from features.program.repository import DbProgramRepository, DbProgramRulesRepository
from features.rest_timer.gateway import WebPushSender
from features.rest_timer.protocol import PushSender, RestTimerRepository
from features.rest_timer.repository import DbRestTimerRepository
from features.training_log.protocol import TrainingLogRepository
from features.training_log.repository import DbTrainingLogRepository
from worker.app import celery_app


def get_session() -> Generator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]


def get_today() -> date:
    return to_local_date(datetime.now(UTC), timezone=ZoneInfo(settings.app_timezone))


def get_job_queue() -> JobQueue:
    return CeleryJobQueue(celery_app)


def get_exercise_repository(session: SessionDep) -> ExerciseRepository:
    return DbExerciseRepository(session)


def get_program_repository(session: SessionDep) -> ProgramRepository:
    return DbProgramRepository(session)


def get_program_rules_repository(session: SessionDep) -> ProgramRulesRepository:
    return DbProgramRulesRepository(session)


def get_training_log_repository(session: SessionDep) -> TrainingLogRepository:
    return DbTrainingLogRepository(session)


def get_rest_timer_repository(session: SessionDep) -> RestTimerRepository:
    return DbRestTimerRepository(session)


def get_push_sender() -> PushSender:
    return WebPushSender(
        vapid_private_key=settings.vapid_private_key.get_secret_value(), vapid_subject=settings.vapid_subject
    )
