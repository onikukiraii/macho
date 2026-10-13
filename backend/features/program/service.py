from datetime import date
from uuid import uuid4

from features.program import _pure
from features.program.protocol import ProgramRepository
from features.program.types import NewProgram, Program, ProgramDayInWeek, Weekday


def get_current_program(repo: ProgramRepository) -> Program | None:
    return repo.get_latest()


def get_program_in_progress_on(repo: ProgramRepository, *, on: date) -> Program | None:
    return repo.get_latest_started_on_or_before(on)


def create_program(repo: ProgramRepository, *, program: NewProgram) -> Program:
    ordered = _pure.sort_weeks_and_days(program)
    day_count = sum(len(week.days) for week in ordered.weeks)
    return repo.create(uid=str(uuid4()), day_uids=[str(uuid4()) for _ in range(day_count)], program=ordered)


def calculate_guide_date(start_date: date, *, week: int, weekday: Weekday) -> date:
    return _pure.calculate_guide_date(start_date, week=week, weekday=weekday)


def list_days_in_order(program: Program) -> list[ProgramDayInWeek]:
    return _pure.list_days_in_order(program)
