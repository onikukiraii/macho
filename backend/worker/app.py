from celery import Celery

from common.config import settings

celery_app = Celery("app", broker=settings.celery_broker_url, include=["worker.tasks"])
