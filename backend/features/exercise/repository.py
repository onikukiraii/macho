from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from common.db.entities import ExerciseRow, TrainingMaxEvaluationRow, TrainingMaxRow
from common.errors import Conflict, NotFound
from features.exercise.types import BodyPart, Exercise, ExerciseFields, TrainingMax, TrainingMaxSource


class DbExerciseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> list[Exercise]:
        rows = self._session.execute(select(ExerciseRow).order_by(ExerciseRow.id)).scalars().all()
        return [_to_domain(row) for row in rows]

    def get(self, uid: str) -> Exercise:
        return _to_domain(self._get_row(uid))

    def create(self, *, uid: str, fields: ExerciseFields) -> Exercise:
        row = ExerciseRow(uid=uid)
        _apply_fields(row, fields)
        self._session.add(row)
        self._commit_exercise()
        self._session.refresh(row)
        return _to_domain(row)

    def update(self, uid: str, *, fields: ExerciseFields) -> Exercise:
        row = self._get_row(uid)
        _apply_fields(row, fields)
        self._commit_exercise()
        self._session.refresh(row)
        return _to_domain(row)

    def list_training_maxes(self) -> list[TrainingMax]:
        statement = select(TrainingMaxRow).order_by(TrainingMaxRow.effective_at.desc(), TrainingMaxRow.id.desc())
        return [_to_training_max(row) for row in self._session.execute(statement).scalars().all()]

    def add_training_max(self, training_max: TrainingMax) -> None:
        self._session.add(_to_training_max_row(training_max))
        self._session.commit()

    def is_week_evaluated(self, week_start: date) -> bool:
        statement = select(TrainingMaxEvaluationRow.id).where(TrainingMaxEvaluationRow.week_start == week_start)
        return self._session.execute(statement).scalar_one_or_none() is not None

    def save_weekly_evaluation(self, *, week_start: date, training_maxes: Sequence[TrainingMax]) -> None:
        self._session.add_all([_to_training_max_row(training_max) for training_max in training_maxes])
        self._session.add(TrainingMaxEvaluationRow(week_start=week_start))
        try:
            self._session.commit()
        except IntegrityError as e:
            self._session.rollback()
            raise Conflict("この週は評価済みです") from e

    def _get_row(self, uid: str) -> ExerciseRow:
        row = self._session.execute(select(ExerciseRow).where(ExerciseRow.uid == uid)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"種目が見つかりません: uid={uid}")
        return row

    def _commit_exercise(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as e:
            self._session.rollback()
            raise Conflict("同じ名前の種目があります") from e


def _apply_fields(row: ExerciseRow, fields: ExerciseFields) -> None:
    row.name = fields.name
    row.body_part = fields.body_part
    row.parent_id = fields.parent_id
    row.coefficient = fields.coefficient
    row.e1rm_divisor = fields.e1rm_divisor
    row.increment_kg = fields.increment_kg
    row.default_rest_seconds = fields.default_rest_seconds


def _to_domain(row: ExerciseRow) -> Exercise:
    return Exercise(
        id=row.id,
        uid=row.uid,
        name=row.name,
        body_part=BodyPart(row.body_part),
        parent_id=row.parent_id,
        coefficient=row.coefficient,
        e1rm_divisor=row.e1rm_divisor,
        increment_kg=row.increment_kg,
        default_rest_seconds=row.default_rest_seconds,
    )


def _to_training_max_row(training_max: TrainingMax) -> TrainingMaxRow:
    return TrainingMaxRow(
        exercise_id=training_max.exercise_id,
        value=training_max.value,
        effective_at=training_max.effective_at,
        source=training_max.source,
        reason=training_max.reason,
    )


def _to_training_max(row: TrainingMaxRow) -> TrainingMax:
    return TrainingMax(
        exercise_id=row.exercise_id,
        value=row.value,
        effective_at=row.effective_at,
        source=TrainingMaxSource(row.source),
        reason=row.reason,
    )
