from collections.abc import Sequence
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from common.db.entities import PlannedExerciseRow, ProgramDayRow, ProgramRow, ProgramWeekRow
from common.errors import Conflict
from features.program.types import (
    NewProgram,
    PlannedExercise,
    Program,
    ProgramDay,
    ProgramWeek,
    Weekday,
)


class DbProgramRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_latest(self) -> Program | None:
        return self._get_first(select(ProgramRow))

    def get_latest_started_on_or_before(self, on: date) -> Program | None:
        return self._get_first(select(ProgramRow).where(ProgramRow.start_date <= on))

    def create(self, *, uid: str, day_uids: Sequence[str], program: NewProgram) -> Program:
        if len(day_uids) != sum(len(week.days) for week in program.weeks):
            raise ValueError("day_uids の件数が Day の件数と一致しません")
        day_uid_iter = iter(day_uids)
        row = ProgramRow(
            uid=uid,
            name=program.name,
            start_date=program.start_date,
            tm_auto_update=program.tm_auto_update,
            design_note=program.design_note,
            weeks=[
                ProgramWeekRow(
                    week=week.week,
                    label=week.label,
                    days=[
                        ProgramDayRow(
                            uid=next(day_uid_iter),
                            day=day.day,
                            weekday=day.weekday,
                            planned_exercises=[
                                PlannedExerciseRow(
                                    exercise_id=planned.exercise_id,
                                    sort_order=planned.order,
                                    sets=planned.sets,
                                    reps=planned.reps,
                                    reps_max=planned.reps_max,
                                    target_rpe=planned.target_rpe,
                                    target_percent=planned.target_percent,
                                )
                                for planned in day.planned_exercises
                            ],
                        )
                        for day in week.days
                    ],
                )
                for week in program.weeks
            ],
        )
        self._session.add(row)
        try:
            self._session.commit()
        except IntegrityError as e:
            self._session.rollback()
            raise Conflict(f"プログラムを保存できませんでした: uid={uid}") from e
        self._session.refresh(row)
        return _to_domain(row)

    def _get_first(self, statement: Select[ProgramRow]) -> Program | None:
        statement = statement.options(
            selectinload(ProgramRow.weeks)
            .selectinload(ProgramWeekRow.days)
            .selectinload(ProgramDayRow.planned_exercises)
        ).order_by(ProgramRow.start_date.desc(), ProgramRow.id.desc())
        row = self._session.execute(statement).scalars().first()
        return None if row is None else _to_domain(row)


def _to_domain(row: ProgramRow) -> Program:
    return Program(
        id=row.id,
        uid=row.uid,
        name=row.name,
        start_date=row.start_date,
        tm_auto_update=row.tm_auto_update,
        design_note=row.design_note,
        weeks=tuple(
            ProgramWeek(
                week=week.week,
                label=week.label,
                days=tuple(
                    ProgramDay(
                        id=day.id,
                        uid=day.uid,
                        day=day.day,
                        weekday=Weekday(day.weekday),
                        planned_exercises=tuple(
                            PlannedExercise(
                                id=planned.id,
                                exercise_id=planned.exercise_id,
                                order=planned.sort_order,
                                sets=planned.sets,
                                reps=planned.reps,
                                reps_max=planned.reps_max,
                                target_rpe=planned.target_rpe,
                                target_percent=planned.target_percent,
                            )
                            for planned in day.planned_exercises
                        ),
                    )
                    for day in week.days
                ),
            )
            for week in row.weeks
        ),
    )
