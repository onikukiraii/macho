from typing import Protocol

from pydantic import BaseModel


class Storage(Protocol):
    def put(self, key: str, body: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def presigned_url(self, key: str, expires_in: int = 3600) -> str: ...


class LLM(Protocol):
    def complete[T: BaseModel](self, *, system: str, prompt: str, output: type[T], trace_id: str) -> T: ...


class JobQueue(Protocol):
    def enqueue(self, task_name: str, **kwargs: str | int) -> str: ...
