from sqlalchemy import select
from sqlalchemy.orm import Session

from common.db.entities import ExerciseRow
from scripts.update_exercises import COMMON_EXERCISES, add_common_exercises, set_all_rest_seconds


def _add_exercise(session: Session, name: str, *, default_rest_seconds: int) -> None:
    session.add(
        ExerciseRow(uid=name, name=name, body_part="chest", increment_kg=2.5, default_rest_seconds=default_rest_seconds)
    )
    session.commit()


class TestSetAllRestSeconds:
    def test_すべての種目のレストを指定した秒数にする(self, db_session: Session) -> None:
        _add_exercise(db_session, "スクワット", default_rest_seconds=180)
        _add_exercise(db_session, "サイドレイズ", default_rest_seconds=90)

        set_all_rest_seconds(db_session, seconds=30)

        assert db_session.execute(select(ExerciseRow.default_rest_seconds)).scalars().all() == [30, 30]


class TestAddCommonExercises:
    def test_同じ名前の種目が既にあるものは追加しない(self, db_session: Session) -> None:
        existing_name = COMMON_EXERCISES[0][0]
        _add_exercise(db_session, existing_name, default_rest_seconds=90)

        added = add_common_exercises(db_session)

        assert added == [name for name, _ in COMMON_EXERCISES[1:]]
        names = db_session.execute(select(ExerciseRow.name)).scalars().all()
        assert sorted(names) == sorted(name for name, _ in COMMON_EXERCISES)
