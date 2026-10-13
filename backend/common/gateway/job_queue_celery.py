from celery import Celery


class CeleryJobQueue:
    def __init__(self, app: Celery) -> None:
        self._app = app

    def enqueue(self, task_name: str, **kwargs: str | int) -> str:
        result = self._app.send_task(task_name, kwargs=kwargs)
        return str(result.id)
