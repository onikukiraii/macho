from datetime import date
from uuid import uuid4

from features.program.protocol import ProgramRepository
from features.program.types import NewProgram, Program


def get_current_program(repo: ProgramRepository) -> Program | None:
    return repo.get_latest()


def get_program_in_progress_on(repo: ProgramRepository, *, on: date) -> Program | None:
    return repo.get_latest_started_on_or_before(on)


def create_program(repo: ProgramRepository, *, program: NewProgram) -> Program:
    day_count = sum(len(week.days) for week in program.weeks)
    return repo.create(uid=str(uuid4()), day_uids=[str(uuid4()) for _ in range(day_count)], program=program)
