from celery import Celery
from kombu.exceptions import OperationalError

from common.errors import JobQueueUnavailable


class CeleryJobQueue:
    def __init__(self, app: Celery) -> None:
        self._app = app

    def enqueue(
        self,
        task_name: str,
        *,
        countdown_seconds: int | None = None,
        expires_seconds: int | None = None,
        **kwargs: str | int,
    ) -> str:
        try:
            result = self._app.send_task(task_name, kwargs=kwargs, countdown=countdown_seconds, expires=expires_seconds)
        except OperationalError as e:
            raise JobQueueUnavailable(f"ジョブを登録できませんでした: task_name={task_name}") from e
        return str(result.id)
