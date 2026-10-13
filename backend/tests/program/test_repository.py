from datetime import date

import pytest
from sqlalchemy.orm import Session

from common.errors import Conflict
from features.exercise.repository import DbExerciseRepository
from features.exercise.types import ExerciseFields
from features.program.repository import DbProgramRepository
from features.program.types import NewPlannedExercise, NewProgram, NewProgramDay, NewProgramWeek, Weekday


def _planned(*, exercise_id: int, order: int) -> NewPlannedExercise:
    return NewPlannedExercise(
        exercise_id=exercise_id, order=order, sets=3, reps=5, reps_max=None, target_rpe=None, target_percent=75.0
    )


def _program(*, name: str, start_date: date, exercise_id: int) -> NewProgram:
    return NewProgram(
        name=name,
        start_date=start_date,
        tm_auto_update=True,
        design_note="",
        weeks=(
            NewProgramWeek(
                week=1,
                label="A",
                days=(
                    NewProgramDay(day=1, weekday=Weekday.mon, planned_exercises=()),
                    NewProgramDay(
                        day=2,
                        weekday=Weekday.wed,
                        planned_exercises=(
                            _planned(exercise_id=exercise_id, order=2),
                            _planned(exercise_id=exercise_id, order=1),
                        ),
                    ),
                ),
            ),
            NewProgramWeek(
                week=2,
                label="B",
                days=(
                    NewProgramDay(
                        day=1, weekday=Weekday.mon, planned_exercises=(_planned(exercise_id=exercise_id, order=1),)
                    ),
                ),
            ),
        ),
    )


def _exercise_id(db_session: Session) -> int:
    fields = ExerciseFields(
        name="スクワット",
        parent_id=None,
        coefficient=None,
        e1rm_divisor=33.3,
        increment_kg=2.5,
        default_rest_seconds=180,
    )
    return DbExerciseRepository(db_session).create(uid="squat", fields=fields).id


class TestCreate:
    def test_作成したプログラムは週と_Day_と予定種目が順に並ぶ(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)

        created = repo.create(
            uid="p1",
            day_uids=["d1", "d2", "d3"],
            program=_program(name="増量期", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )

        assert [week.week for week in created.weeks] == [1, 2]
        assert [day.day for day in created.weeks[0].days] == [1, 2]
        assert [planned.order for planned in created.weeks[0].days[1].planned_exercises] == [1, 2]

    def test_予定種目の全フィールドを入力のとおりに保存して取得できる(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)
        new_program = NewProgram(
            name="減量期",
            start_date=date(2026, 11, 4),
            tm_auto_update=False,
            design_note="deload 前提",
            weeks=(
                NewProgramWeek(
                    week=3,
                    label="deload",
                    days=(
                        NewProgramDay(
                            day=4,
                            weekday=Weekday.thu,
                            planned_exercises=(
                                NewPlannedExercise(
                                    exercise_id=exercise_id,
                                    order=7,
                                    sets=4,
                                    reps=6,
                                    reps_max=8,
                                    target_rpe=8.5,
                                    target_percent=82.5,
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

        created = repo.create(uid="p1", day_uids=["d1"], program=new_program)

        fetched = repo.get_latest()
        assert fetched == created
        assert (created.uid, created.name, created.start_date, created.tm_auto_update, created.design_note) == (
            "p1",
            "減量期",
            date(2026, 11, 4),
            False,
            "deload 前提",
        )
        week = created.weeks[0]
        assert (week.week, week.label) == (3, "deload")
        day = week.days[0]
        assert (day.uid, day.day, day.weekday) == ("d1", 4, Weekday.thu)
        planned = day.planned_exercises[0]
        assert (
            planned.exercise_id,
            planned.order,
            planned.sets,
            planned.reps,
            planned.reps_max,
            planned.target_rpe,
            planned.target_percent,
        ) == (exercise_id, 7, 4, 6, 8, 8.5, 82.5)

    def test_Day_の_uid_は渡した順に週と_Day_の並びへ割り当てる(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)

        created = repo.create(
            uid="p1",
            day_uids=["d1", "d2", "d3"],
            program=_program(name="増量期", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )

        assert [day.uid for week in created.weeks for day in week.days] == ["d1", "d2", "d3"]

    @pytest.mark.parametrize("day_uids", [["d1", "d2"], ["d1", "d2", "d3", "d4"]])
    def test_Day_の_uid_の件数が_Day_の件数と合わなければ例外(self, db_session: Session, day_uids: list[str]) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)

        with pytest.raises(ValueError):
            repo.create(
                uid="p1",
                day_uids=day_uids,
                program=_program(name="増量期", start_date=date(2026, 9, 28), exercise_id=exercise_id),
            )

    def test_週番号が重複すると_Conflict_になりセッションは使える(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)
        duplicated = NewProgram(
            name="重複",
            start_date=date(2026, 9, 28),
            tm_auto_update=True,
            design_note="",
            weeks=(
                NewProgramWeek(week=1, label="A", days=()),
                NewProgramWeek(week=1, label="B", days=()),
            ),
        )

        with pytest.raises(Conflict):
            repo.create(uid="p1", day_uids=[], program=duplicated)

        created = repo.create(
            uid="p2",
            day_uids=["d1", "d2", "d3"],
            program=_program(name="増量期", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )
        assert repo.get_latest() == created

    def test_同じ週の_Day_番号が重複すると_Conflict_になる(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        duplicated = NewProgram(
            name="重複",
            start_date=date(2026, 9, 28),
            tm_auto_update=True,
            design_note="",
            weeks=(
                NewProgramWeek(
                    week=1,
                    label="A",
                    days=(
                        NewProgramDay(day=1, weekday=Weekday.mon, planned_exercises=()),
                        NewProgramDay(day=1, weekday=Weekday.wed, planned_exercises=()),
                    ),
                ),
            ),
        )

        with pytest.raises(Conflict):
            repo.create(uid="p1", day_uids=["d1", "d2"], program=duplicated)


class TestGetLatest:
    def test_プログラムが無ければ_None(self, db_session: Session) -> None:
        assert DbProgramRepository(db_session).get_latest() is None

    def test_開始日が最も新しいプログラムを返す(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)
        repo.create(
            uid="new",
            day_uids=["d", "e", "f"],
            program=_program(name="新", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )
        repo.create(
            uid="old",
            day_uids=["a", "b", "c"],
            program=_program(name="旧", start_date=date(2026, 3, 2), exercise_id=exercise_id),
        )

        latest = repo.get_latest()

        assert latest is not None
        assert latest.name == "新"

    def test_開始日が同じなら後から作成したプログラムを返す(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)
        repo.create(
            uid="first",
            day_uids=["a", "b", "c"],
            program=_program(name="先", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )
        repo.create(
            uid="second",
            day_uids=["d", "e", "f"],
            program=_program(name="後", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )

        latest = repo.get_latest()

        assert latest is not None
        assert latest.name == "後"


class TestGetLatestStartedOnOrBefore:
    def test_指定日以前に開始した中で最も新しいプログラムを返す(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)
        repo.create(
            uid="older",
            day_uids=["g", "h", "i"],
            program=_program(name="最古", start_date=date(2026, 1, 5), exercise_id=exercise_id),
        )
        repo.create(
            uid="old",
            day_uids=["a", "b", "c"],
            program=_program(name="旧", start_date=date(2026, 3, 2), exercise_id=exercise_id),
        )
        repo.create(
            uid="new",
            day_uids=["d", "e", "f"],
            program=_program(name="新", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )

        found = repo.get_latest_started_on_or_before(date(2026, 9, 27))

        assert found is not None
        assert found.name == "旧"

    def test_開始日当日は含める(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)
        repo.create(
            uid="new",
            day_uids=["d", "e", "f"],
            program=_program(name="新", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )

        found = repo.get_latest_started_on_or_before(date(2026, 9, 28))

        assert found is not None
        assert found.name == "新"

    def test_指定日以前に開始したプログラムが無ければ_None(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)
        repo.create(
            uid="new",
            day_uids=["d", "e", "f"],
            program=_program(name="新", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )

        assert repo.get_latest_started_on_or_before(date(2026, 9, 27)) is None
