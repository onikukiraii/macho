from dataclasses import replace
from datetime import date, timedelta

from features.program.types import (
    NewProgram,
    NewProgramWeek,
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
