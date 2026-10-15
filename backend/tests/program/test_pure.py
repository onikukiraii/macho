from datetime import date

import pytest

from features.program._pure import calculate_guide_date, list_days_in_order, list_past_programs
from features.program.types import Program, ProgramDay, ProgramWeek, Weekday


def _day(*, id: int, day: int, weekday: Weekday) -> ProgramDay:
    return ProgramDay(id=id, uid=f"day-{id}", day=day, weekday=weekday, planned_exercises=())


class TestCalculateGuideDate:
    @pytest.mark.parametrize(
        ("week", "weekday", "expected"),
        [
            (1, Weekday.mon, date(2026, 9, 28)),
            (1, Weekday.sun, date(2026, 10, 4)),
            (2, Weekday.wed, date(2026, 10, 7)),
            (5, Weekday.fri, date(2026, 10, 30)),
        ],
    )
    def test_開始日の週の月曜を起点に目安日を出す(self, week: int, weekday: Weekday, expected: date) -> None:
        assert calculate_guide_date(date(2026, 9, 28), week=week, weekday=weekday) == expected

    @pytest.mark.parametrize(
        ("start_date", "week", "weekday", "expected"),
        [
            (date(2026, 9, 30), 1, Weekday.mon, date(2026, 9, 28)),
            (date(2026, 9, 30), 2, Weekday.fri, date(2026, 10, 9)),
            (date(2026, 10, 4), 1, Weekday.mon, date(2026, 9, 28)),
            (date(2026, 10, 4), 2, Weekday.sun, date(2026, 10, 11)),
        ],
    )
    def test_開始日が週の途中でもその週の月曜を起点に目安日を出す(
        self, start_date: date, week: int, weekday: Weekday, expected: date
    ) -> None:
        assert calculate_guide_date(start_date, week=week, weekday=weekday) == expected


class TestListDaysInOrder:
    def test_週と_Day_の昇順に並べる(self) -> None:
        program = Program(
            id=1,
            uid="p",
            name="増量期",
            start_date=date(2026, 9, 28),
            tm_auto_update=True,
            design_note="",
            weeks=(
                ProgramWeek(week=2, label="B", days=(_day(id=3, day=1, weekday=Weekday.mon),)),
                ProgramWeek(
                    week=1,
                    label="A",
                    days=(_day(id=2, day=2, weekday=Weekday.wed), _day(id=1, day=1, weekday=Weekday.mon)),
                ),
            ),
        )

        ordered = [(entry.week.week, entry.day.day) for entry in list_days_in_order(program)]

        assert ordered == [(1, 1), (1, 2), (2, 1)]


def _program(*, id: int, name: str, start_date: date) -> Program:
    return Program(
        id=id,
        uid=f"program-{id}",
        name=name,
        start_date=start_date,
        tm_auto_update=True,
        design_note="",
        weeks=(ProgramWeek(week=1, label="A", days=(_day(id=id, day=1, weekday=Weekday.mon),)),),
    )


class TestListPastPrograms:
    @pytest.mark.parametrize(
        ("programs", "expected"),
        [
            (
                [
                    _program(id=1, name="2026 増量期", start_date=date(2026, 9, 28)),
                    _program(id=3, name="ベンチ スモロフ Jr", start_date=date(2026, 10, 19)),
                    _program(id=2, name="2026 減量期", start_date=date(2026, 6, 1)),
                ],
                [("2026 増量期", date(2026, 10, 18)), ("2026 減量期", date(2026, 9, 27))],
            ),
            ([_program(id=1, name="2026 増量期", start_date=date(2026, 9, 28))], []),
            ([], []),
        ],
    )
    def test_最新以外を開始日の新しい順に並べ終了日を次のプログラムの開始日の前日にする(
        self, programs: list[Program], expected: list[tuple[str, date]]
    ) -> None:
        assert [(past.program.name, past.end_date) for past in list_past_programs(programs)] == expected
