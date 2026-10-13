from collections.abc import Sequence
from datetime import date
from typing import Protocol

from features.program.types import NewProgram, Program


class ProgramRepository(Protocol):
    def get_latest(self) -> Program | None: ...

    def get_latest_started_on_or_before(self, on: date) -> Program | None: ...

    def create(self, *, uid: str, day_uids: Sequence[str], program: NewProgram) -> Program: ...
