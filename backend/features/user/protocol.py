from typing import Protocol

from features.user.types import User


class UserRepository(Protocol):
    def list_all(self) -> list[User]: ...

    def create(self, *, name: str, email: str) -> User: ...
