from collections.abc import Generator
from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends
from sqlalchemy.orm import Session

from common.config import settings
from common.db.session import SessionLocal
from common.gateway.job_queue_celery import CeleryJobQueue
from common.gateway.protocol import JobQueue
from worker.app import celery_app


def get_session() -> Generator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]


def get_today() -> date:
    return datetime.now(ZoneInfo(settings.app_timezone)).date()


def get_job_queue() -> JobQueue:
    return CeleryJobQueue(celery_app)
