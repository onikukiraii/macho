from collections.abc import Sequence
from dataclasses import replace
from datetime import date, timedelta

from features.program.types import (
    NewProgram,
    NewProgramWeek,
    PastProgram,
    Program,
    ProgramDayInWeek,
    Weekday,
)

_WEEKDAYS = list(Weekday)


def calculate_guide_date(start_date: date, *, week: int, weekday: Weekday) -> date:
    week_monday = start_date - timedelta(days=start_date.weekday())
    return week_monday + timedelta(weeks=week - 1, days=_WEEKDAYS.index(weekday))


def list_days_in_order(program: Program) -> list[ProgramDayInWeek]:
    return [
        ProgramDayInWeek(week=week, day=day)
        for week in sorted(program.weeks, key=lambda week: week.week)
        for day in sorted(week.days, key=lambda day: day.day)
    ]


def sort_weeks_and_days(program: NewProgram) -> NewProgram:
    return replace(
        program,
        weeks=tuple(
            NewProgramWeek(
                week=week.week,
                label=week.label,
                days=tuple(sorted(week.days, key=lambda day: day.day)),
            )
            for week in sorted(program.weeks, key=lambda week: week.week)
        ),
    )


def list_past_programs(programs: Sequence[Program]) -> list[PastProgram]:
    newest_first = sorted(programs, key=lambda program: (program.start_date, program.id), reverse=True)
    return [
        PastProgram(program=program, end_date=successor.start_date - timedelta(days=1))
        for successor, program in zip(newest_first, newest_first[1:], strict=False)
    ]
