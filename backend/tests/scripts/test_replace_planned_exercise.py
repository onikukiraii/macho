from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from common.db.entities import (
    ExerciseRow,
    PlannedExerciseRow,
    ProgramDayRow,
    ProgramRow,
    ProgramWeekRow,
    TrainingLogRow,
)
from scripts.replace_planned_exercise import ExerciseNotFound, replace_planned_exercise


def _add_exercise(session: Session, name: str) -> ExerciseRow:
    exercise = ExerciseRow(uid=name, name=name, body_part="back", increment_kg=2.5, default_rest_seconds=90)
    session.add(exercise)
    session.flush()
    return exercise


def _day(day: int, *, exercise_id: int) -> ProgramDayRow:
    return ProgramDayRow(
        uid=f"day-{day}",
        day=day,
        weekday="mon",
        planned_exercises=[PlannedExerciseRow(exercise_id=exercise_id, sort_order=1, sets=3, reps=10)],
    )


class TestReplacePlannedExercise:
    def test_記録の無い_Day_の予定だけを差し替える(self, db_session: Session) -> None:
        lat_pulldown = _add_exercise(db_session, "ラットプルダウン")
        pull_up = _add_exercise(db_session, "懸垂")
        recorded_day = _day(1, exercise_id=lat_pulldown.id)
        pending_day = _day(2, exercise_id=lat_pulldown.id)
        db_session.add(
            ProgramRow(
                uid="program",
                name="増量期",
                start_date=date(2026, 9, 28),
                tm_auto_update=True,
                design_note="",
                weeks=[ProgramWeekRow(week=1, label="", days=[recorded_day, pending_day])],
            )
        )
        db_session.flush()
        db_session.add(TrainingLogRow(uid="log", date=date(2026, 9, 28), program_day_id=recorded_day.id, memo=""))
        db_session.commit()

        replace_planned_exercise(db_session, from_name="ラットプルダウン", to_name="懸垂")

        planned = db_session.execute(select(PlannedExerciseRow.program_day_id, PlannedExerciseRow.exercise_id)).all()
        assert sorted(planned) == [(recorded_day.id, lat_pulldown.id), (pending_day.id, pull_up.id)]

    def test_差し替え先の種目が無いときは中断する(self, db_session: Session) -> None:
        _add_exercise(db_session, "ラットプルダウン")
        db_session.commit()

        with pytest.raises(ExerciseNotFound, match="懸垂"):
            replace_planned_exercise(db_session, from_name="ラットプルダウン", to_name="懸垂")
