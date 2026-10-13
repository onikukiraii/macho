from datetime import date, timedelta

from features.program.types import Program, ProgramDay, ProgramWeek, Weekday

_WEEKDAYS = list(Weekday)


def calculate_guide_date(start_date: date, *, week: int, weekday: Weekday) -> date:
    return start_date + timedelta(weeks=week - 1, days=_WEEKDAYS.index(weekday))


def list_days_in_order(program: Program) -> list[tuple[ProgramWeek, ProgramDay]]:
    return [
        (week, day)
        for week in sorted(program.weeks, key=lambda week: week.week)
        for day in sorted(week.days, key=lambda day: day.day)
    ]
