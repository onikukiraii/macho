from collections.abc import Collection, Sequence
from datetime import date

from sqlalchemy import ColumnElement, Select, and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from common.db.entities import ExerciseSetRow, PerformedExerciseRow, TrainingLogRow
from common.errors import Conflict, NotFound
from features.training_log.types import (
    ExerciseHistoryEntry,
    ExerciseSet,
    NewPerformedExercise,
    PerformedExercise,
    PreviousPerformance,
    TrainingLog,
)


class DbTrainingLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, uid: str) -> TrainingLog:
        return _to_domain(self._get_row(uid))

    def get_by_performed_uid(self, performed_uid: str) -> TrainingLog:
        return _to_domain(self._get_performed_row(performed_uid, for_update=False).training_log)

    def get_latest(self) -> TrainingLog | None:
        statement = _select_logs().order_by(TrainingLogRow.date.desc(), TrainingLogRow.id.desc())
        row = self._session.execute(statement).scalars().first()
        return None if row is None else _to_domain(row)

    def list_between(self, *, from_date: date, to_date: date) -> list[TrainingLog]:
        return self._list(TrainingLogRow.date.between(from_date, to_date))

    def list_on_or_before(self, to_date: date) -> list[TrainingLog]:
        return self._list(TrainingLogRow.date <= to_date)

    def count_sets_between(self, *, from_date: date, to_date: date) -> int:
        statement = (
            select(func.count(ExerciseSetRow.id))
            .join(ExerciseSetRow.performed_exercise)
            .join(PerformedExerciseRow.training_log)
            .where(TrainingLogRow.date.between(from_date, to_date))
        )
        return self._session.execute(statement).scalar_one()

    def list_last_recorded_dates(self, program_day_ids: Collection[int]) -> dict[int, date]:
        statement = (
            select(TrainingLogRow.program_day_id, func.max(TrainingLogRow.date))
            .where(TrainingLogRow.program_day_id.in_(program_day_ids))
            .group_by(TrainingLogRow.program_day_id)
        )
        return {
            program_day_id: last_date
            for program_day_id, last_date in self._session.execute(statement)
            if program_day_id is not None
        }

    def find_previous_performance(self, *, exercise_id: int, before: TrainingLog) -> PreviousPerformance | None:
        is_earlier = or_(
            TrainingLogRow.date < before.date,
            and_(TrainingLogRow.date == before.date, TrainingLogRow.id < before.id),
        )
        statement = (
            _select_performed_with_sets(exercise_id)
            .where(is_earlier)
            .order_by(
                TrainingLogRow.date.desc(),
                TrainingLogRow.id.desc(),
                PerformedExerciseRow.sort_order.desc(),
                PerformedExerciseRow.id.desc(),
            )
        )
        row = self._session.execute(statement).scalars().first()
        if row is None:
            return None
        return PreviousPerformance(date=row.training_log.date, sets=_to_sets(row))

    def list_exercise_history(self, exercise_id: int) -> list[ExerciseHistoryEntry]:
        statement = _select_performed_with_sets(exercise_id).order_by(
            TrainingLogRow.date.desc(),
            TrainingLogRow.id.desc(),
            PerformedExerciseRow.sort_order,
            PerformedExerciseRow.id,
        )
        return [
            ExerciseHistoryEntry(
                training_log_uid=row.training_log.uid,
                date=row.training_log.date,
                program_day_id=row.training_log.program_day_id,
                sets=_to_sets(row),
            )
            for row in self._session.execute(statement).scalars().all()
        ]

    def create(
        self, *, uid: str, date: date, program_day_id: int | None, exercises: Sequence[NewPerformedExercise]
    ) -> TrainingLog:
        row = TrainingLogRow(
            uid=uid,
            date=date,
            program_day_id=program_day_id,
            memo="",
            performed_exercises=[_to_performed_row(exercise) for exercise in exercises],
        )
        self._session.add(row)
        self._session.commit()
        return self.get(uid)

    def update_memo(self, uid: str, *, memo: str) -> TrainingLog:
        row = self._get_row(uid)
        row.memo = memo
        self._session.commit()
        return self.get(uid)

    def add_exercise(self, uid: str, *, exercise: NewPerformedExercise) -> TrainingLog:
        row = self._get_row(uid)
        row.performed_exercises.append(_to_performed_row(exercise))
        self._session.commit()
        return self.get(uid)

    def replace_performed_exercise(self, performed_uid: str, *, exercise_id: int) -> TrainingLog:
        row = self._get_performed_row(performed_uid, for_update=True)
        row.exercise_id = exercise_id
        self._session.commit()
        return self.get_by_performed_uid(performed_uid)

    def update_performed_exercise_memo(self, performed_uid: str, *, memo: str) -> TrainingLog:
        row = self._get_performed_row(performed_uid, for_update=True)
        row.memo = memo
        self._session.commit()
        return self.get_by_performed_uid(performed_uid)

    def replace_sets(self, performed_uid: str, *, sets: Sequence[ExerciseSet]) -> TrainingLog:
        row = self._get_performed_row(performed_uid, for_update=True)
        # 前のセットの DELETE を先に flush する。同じ番号の INSERT が先に実行されると一意制約に違反する
        row.sets = []
        self._session.flush()
        row.sets = [
            ExerciseSetRow(
                sort_order=exercise_set.order, weight=exercise_set.weight, reps=exercise_set.reps, rir=exercise_set.rir
            )
            for exercise_set in sets
        ]
        try:
            self._session.commit()
        except IntegrityError as e:
            self._session.rollback()
            raise Conflict(f"同じ番号のセットがあります: uid={performed_uid}") from e
        return self.get_by_performed_uid(performed_uid)

    def delete(self, uid: str) -> None:
        self._session.delete(self._get_row(uid))
        self._session.commit()

    def _list(self, condition: ColumnElement[bool]) -> list[TrainingLog]:
        statement = _select_logs().where(condition).order_by(TrainingLogRow.date, TrainingLogRow.id)
        return [_to_domain(row) for row in self._session.execute(statement).scalars().all()]

    def _get_row(self, uid: str) -> TrainingLogRow:
        row = self._session.execute(_select_logs().where(TrainingLogRow.uid == uid)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"トレーニング記録が見つかりません: uid={uid}")
        return row

    def _get_performed_row(self, performed_uid: str, *, for_update: bool) -> PerformedExerciseRow:
        statement = select(PerformedExerciseRow).where(PerformedExerciseRow.uid == performed_uid)
        if for_update:
            statement = statement.with_for_update()
        row = self._session.execute(statement).scalar_one_or_none()
        if row is None:
            raise NotFound(f"実施種目が見つかりません: uid={performed_uid}")
        return row


def _select_logs() -> Select[TrainingLogRow]:
    return select(TrainingLogRow).options(
        selectinload(TrainingLogRow.performed_exercises).selectinload(PerformedExerciseRow.sets)
    )


def _select_performed_with_sets(exercise_id: int) -> Select[PerformedExerciseRow]:
    return (
        select(PerformedExerciseRow)
        .join(PerformedExerciseRow.training_log)
        .where(PerformedExerciseRow.exercise_id == exercise_id, PerformedExerciseRow.sets.any())
        .options(selectinload(PerformedExerciseRow.sets), selectinload(PerformedExerciseRow.training_log))
    )


def _to_performed_row(exercise: NewPerformedExercise) -> PerformedExerciseRow:
    return PerformedExerciseRow(
        uid=exercise.uid,
        exercise_id=exercise.exercise_id,
        planned_exercise_id=exercise.planned_exercise_id,
        sort_order=exercise.order,
        memo="",
    )


def _to_sets(row: PerformedExerciseRow) -> tuple[ExerciseSet, ...]:
    return tuple(
        ExerciseSet(order=set_row.sort_order, weight=set_row.weight, reps=set_row.reps, rir=set_row.rir)
        for set_row in row.sets
    )


def _to_domain(row: TrainingLogRow) -> TrainingLog:
    return TrainingLog(
        id=row.id,
        uid=row.uid,
        date=row.date,
        program_day_id=row.program_day_id,
        memo=row.memo,
        exercises=tuple(
            PerformedExercise(
                id=performed.id,
                uid=performed.uid,
                exercise_id=performed.exercise_id,
                planned_exercise_id=performed.planned_exercise_id,
                order=performed.sort_order,
                memo=performed.memo,
                sets=_to_sets(performed),
            )
            for performed in row.performed_exercises
        ),
    )
