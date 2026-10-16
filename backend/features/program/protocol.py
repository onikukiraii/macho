from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol

from features.program.types import NewProgram, Program, ProgramRules


class ProgramRepository(Protocol):
    def get_latest(self) -> Program | None: ...

    def list_all(self) -> list[Program]: ...

    def get_latest_started_on_or_before(self, on: date) -> Program | None: ...

    def create(self, *, uid: str, day_uids: Sequence[str], program: NewProgram) -> Program: ...


class ProgramRulesRepository(Protocol):
    def get(self) -> ProgramRules: ...

    def save(self, *, body: str, updated_at: datetime) -> ProgramRules: ...
