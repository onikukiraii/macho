import argparse
import logging
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from common.db.entities import ExerciseRow, PlannedExerciseRow, TrainingLogRow
from common.db.session import SessionLocal

logger = logging.getLogger(__name__)


class ExerciseNotFound(Exception): ...


def replace_planned_exercise(session: Session, *, from_name: str, to_name: str) -> int:
    """記録の無い Day の予定に限って種目を差し替え、差し替えた予定の数を返す。

    予定の行は記録から ID で参照されるため、行を作り直さずに種目だけを書き換える。
    記録のある Day は、記録した日の予定を残すため対象から除外する。
    """
    exercise_ids = dict(
        session.execute(select(ExerciseRow.name, ExerciseRow.id).where(ExerciseRow.name.in_([from_name, to_name])))
        .tuples()
        .all()
    )
    missing = [name for name in (from_name, to_name) if name not in exercise_ids]
    if len(missing) > 0:
        raise ExerciseNotFound(f"種目が見つかりません: {', '.join(missing)}")
    recorded_day_ids = select(TrainingLogRow.program_day_id).where(TrainingLogRow.program_day_id.is_not(None))
    planned_ids = (
        session.execute(
            select(PlannedExerciseRow.id).where(
                PlannedExerciseRow.exercise_id == exercise_ids[from_name],
                PlannedExerciseRow.program_day_id.not_in(recorded_day_ids),
            )
        )
        .scalars()
        .all()
    )
    session.execute(
        update(PlannedExerciseRow)
        .where(PlannedExerciseRow.id.in_(planned_ids))
        .values(exercise_id=exercise_ids[to_name])
    )
    session.commit()
    return len(planned_ids)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="記録の無い Day の予定で、種目を別の種目へ差し替える")
    parser.add_argument("--from", dest="from_name", required=True, help="差し替える前の種目名")
    parser.add_argument("--to", dest="to_name", required=True, help="差し替えた後の種目名")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as session:
        try:
            count = replace_planned_exercise(session, from_name=args.from_name, to_name=args.to_name)
        except ExerciseNotFound as error:
            logger.error("%s", error)
            raise SystemExit(1) from error
    logger.info("%s を %s へ差し替えた予定は %d 件です", args.from_name, args.to_name, count)


if __name__ == "__main__":
    main()
