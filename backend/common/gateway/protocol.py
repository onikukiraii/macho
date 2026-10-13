from typing import Protocol


class JobQueue(Protocol):
    def enqueue(self, task_name: str, *, countdown_seconds: int | None = None, **kwargs: str | int) -> str: ...
