from typing import Any

import pytest
from kombu.exceptions import OperationalError

from common.errors import JobQueueUnavailable
from common.gateway.job_queue_celery import CeleryJobQueue


class _Result:
    id = "task-1"


class _FakeCeleryApp:
    def __init__(self, error: Exception | None = None) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []
        self._error = error

    def send_task(self, name: str, **options: Any) -> _Result:
        if self._error:
            raise self._error
        self.sent.append((name, options))
        return _Result()


class TestCeleryJobQueueEnqueue:
    def test_countdown_と_expires_を_send_task_へ渡す(self) -> None:
        app = _FakeCeleryApp()

        job_id = CeleryJobQueue(app).enqueue("t", countdown_seconds=90, expires_seconds=120, uid="u")

        assert job_id == "task-1"
        assert app.sent == [("t", {"kwargs": {"uid": "u"}, "countdown": 90, "expires": 120})]

    def test_ブローカーに接続できなければ_JobQueueUnavailable_にする(self) -> None:
        queue = CeleryJobQueue(_FakeCeleryApp(error=OperationalError("down")))

        with pytest.raises(JobQueueUnavailable):
            queue.enqueue("t")
