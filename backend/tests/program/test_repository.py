from datetime import date

from sqlalchemy.orm import Session

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
                week=2,
                label="B",
                days=(
                    NewProgramDay(
                        day=1, weekday=Weekday.mon, planned_exercises=(_planned(exercise_id=exercise_id, order=1),)
                    ),
                ),
            ),
            NewProgramWeek(
                week=1,
                label="A",
                days=(
                    NewProgramDay(
                        day=2,
                        weekday=Weekday.wed,
                        planned_exercises=(
                            _planned(exercise_id=exercise_id, order=2),
                            _planned(exercise_id=exercise_id, order=1),
                        ),
                    ),
                    NewProgramDay(day=1, weekday=Weekday.mon, planned_exercises=()),
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

        fetched = repo.get_latest()
        assert fetched == created
        assert [week.week for week in created.weeks] == [1, 2]
        assert [day.day for day in created.weeks[0].days] == [1, 2]
        assert [planned.order for planned in created.weeks[0].days[1].planned_exercises] == [1, 2]

    def test_Day_の_uid_は渡した順に週と_Day_の昇順へ割り当てる(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)

        created = repo.create(
            uid="p1",
            day_uids=["d1", "d2", "d3"],
            program=_program(name="増量期", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )

        assert [day.uid for week in created.weeks for day in week.days] == ["d1", "d2", "d3"]


class TestGetLatest:
    def test_プログラムが無ければ_None(self, db_session: Session) -> None:
        assert DbProgramRepository(db_session).get_latest() is None

    def test_開始日が最も新しいプログラムを返す(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)
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

        latest = repo.get_latest()

        assert latest is not None
        assert latest.name == "新"


class TestGetLatestStartedOnOrBefore:
    def test_指定日以前に開始した中で最も新しいプログラムを返す(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)
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

    def test_指定日より前に開始したプログラムが無ければ_None(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        exercise_id = _exercise_id(db_session)
        repo.create(
            uid="new",
            day_uids=["d", "e", "f"],
            program=_program(name="新", start_date=date(2026, 9, 28), exercise_id=exercise_id),
        )

        assert repo.get_latest_started_on_or_before(date(2026, 9, 27)) is None
