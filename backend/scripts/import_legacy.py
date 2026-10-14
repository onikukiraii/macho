import argparse
import csv
import io
import logging
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from itertools import dropwhile, takewhile
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from common.db.session import SessionLocal
from common.errors import Conflict
from dependencies import get_exercise_repository, get_program_repository, get_today, get_training_log_repository
from features.exercise import service as exercise_service
from features.exercise.dto import ExerciseSaveParams
from features.exercise.protocol import ExerciseRepository
from features.exercise.types import Exercise
from features.program import service as program_service
from features.program.protocol import ProgramRepository
from features.program.types import NewPlannedExercise, NewProgram, NewProgramDay, NewProgramWeek, Weekday
from features.training_log import service as training_log_service
from features.training_log.dto import PerformedExerciseUpdateParams, SetsReplaceParams
from features.training_log.protocol import TrainingLogRepository
from features.training_log.types import ExerciseSet

logger = logging.getLogger(__name__)

PROGRAM_NAME = "2026 増量期"
PROGRAM_START_DATE = date(2026, 9, 28)
EXERCISE_NAMES = {
    "ルーマニアンデッドリフト": "ルーマニアンDL",
    "ポーズベンチプレス": "ポーズベンチ",
    "シーテッドレッグプレス": "レッグプレス",
}
MASTER_HEADING = "■ 種目マスタ"
BENCH_PRESS = "ベンチプレス"
BENCH_PRESS_E1RM_DIVISOR = 40.0
DEFAULT_E1RM_DIVISOR = 33.3
INCREMENT_KG = 2.5
MAIN_REST_SECONDS = 180
ACCESSORY_REST_SECONDS = 90
TEST_DAY_PREFIX = "テスト"
TEST_WEEK_PERCENTS = (40.0, 60.0, 75.0, 85.0, 92.0, 100.0)
WEEKDAYS = {
    "月": Weekday.mon,
    "火": Weekday.tue,
    "水": Weekday.wed,
    "木": Weekday.thu,
    "金": Weekday.fri,
    "土": Weekday.sat,
    "日": Weekday.sun,
}
DAY_PATTERN = re.compile(rf"(Day\d+|{TEST_DAY_PREFIX}) [{''.join(WEEKDAYS)}]")


class InvalidLegacyFile(Exception): ...


@dataclass(frozen=True)
class LegacyExercise:
    name: str
    memo: str
    sets: tuple[ExerciseSet, ...]


@dataclass(frozen=True)
class LegacyTrainingLog:
    date: date
    exercises: tuple[LegacyExercise, ...]


@dataclass(frozen=True)
class MasterExercise:
    name: str
    category: str
    coefficient: float


@dataclass(frozen=True)
class PhaseRow:
    week: str
    guide_date: date
    day: str
    exercise_name: str
    sets: int
    reps: int
    target_rpe: float | None
    actual_weight: float | None
    actual_reps: int | None
    actual_rir: int | None


@dataclass(frozen=True)
class ExerciseToCreate:
    name: str
    parent_name: str | None
    coefficient: float | None
    e1rm_divisor: float | None
    default_rest_seconds: int


@dataclass(frozen=True)
class RirRecord:
    date: date
    exercise_name: str
    weight: float
    reps: int
    rir: int


@dataclass(frozen=True)
class RirFilling:
    training_logs: tuple[LegacyTrainingLog, ...]
    unfilled_count: int


def parse_training_csv(text: str) -> list[LegacyTrainingLog]:
    exercises_by_date: dict[date, list[LegacyExercise]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        name = EXERCISE_NAMES.get(row["種目"].strip(), row["種目"].strip())
        # KINNIK は重量の空欄と小数の回数を許す。セットの数を保つため、空欄は 0kg、回数は四捨五入で取り込む
        exercise_set = ExerciseSet(
            order=int(row["セット"]),
            weight=0.0 if row["重量"] == "" else float(row["重量"]),
            reps=int(Decimal(row["レップ数"]).quantize(Decimal(1), rounding=ROUND_HALF_UP)),
            rir=None,
        )
        exercises = exercises_by_date.setdefault(date.fromisoformat(row["日付"]), [])
        is_continued = (
            len(exercises) > 0 and exercises[-1].name == name and exercises[-1].sets[-1].order < exercise_set.order
        )
        if is_continued:
            exercises[-1] = replace(exercises[-1], sets=(*exercises[-1].sets, exercise_set))
        else:
            exercises.append(LegacyExercise(name=name, memo=row["メモ"], sets=(exercise_set,)))
    return [
        LegacyTrainingLog(date=on, exercises=tuple(exercises)) for on, exercises in sorted(exercises_by_date.items())
    ]


def extract_design_note(maintenance_prompt: str) -> str:
    section = dropwhile(lambda line: not line.startswith("## 3."), maintenance_prompt.splitlines())
    if next(section, None) is None:
        raise InvalidLegacyFile("保守プロンプトに「## 3.」の節がありません")
    return "\n".join(takewhile(lambda line: not line.startswith("## "), section)).strip()


def plan_exercises(
    master: Sequence[MasterExercise], training_logs: Sequence[LegacyTrainingLog], *, planned_names: Iterable[str]
) -> list[ExerciseToCreate]:
    base_names = {exercise.category: exercise.name for exercise in master if exercise.coefficient == 1}
    from_master = [
        ExerciseToCreate(
            name=exercise.name,
            parent_name=None if exercise.coefficient == 1 else base_names[exercise.category],
            coefficient=None if exercise.coefficient == 1 else exercise.coefficient,
            e1rm_divisor=_e1rm_divisor(exercise.name) if exercise.coefficient == 1 else None,
            default_rest_seconds=MAIN_REST_SECONDS,
        )
        for exercise in master
    ]
    master_names = {exercise.name for exercise in master}
    performed_names = dict.fromkeys(exercise.name for log in training_logs for exercise in log.exercises)
    planned_names = list(dict.fromkeys(planned_names))
    unperformed_names = [name for name in planned_names if name not in master_names and name not in performed_names]
    if len(unperformed_names) > 0:
        logger.warning(
            "種目マスタにも KINNIK の CSV にも無い予定の種目を作ります。表記のずれでないか確認してください: %s",
            unperformed_names,
        )
    # 増量期の予定にあってまだ実施していない補助種目も、予定種目の参照先として作る
    logged_names = dict.fromkeys([*performed_names, *planned_names])
    from_logs = [
        ExerciseToCreate(
            name=name,
            parent_name=None,
            coefficient=None,
            e1rm_divisor=_e1rm_divisor(name),
            default_rest_seconds=ACCESSORY_REST_SECONDS,
        )
        for name in logged_names
        if name not in master_names
    ]
    return sorted([*from_master, *from_logs], key=lambda exercise: exercise.parent_name is not None)


def build_program(rows: Sequence[PhaseRow], *, design_note: str, exercise_ids: Mapping[str, int]) -> NewProgram:
    rows_by_week: dict[str, dict[str, list[PhaseRow]]] = {}
    for row in rows:
        rows_by_week.setdefault(row.week, {}).setdefault(row.day, []).append(row)
    labels = label_weeks([week.partition(" ")[2] for week in rows_by_week])
    return NewProgram(
        name=PROGRAM_NAME,
        start_date=PROGRAM_START_DATE,
        tm_auto_update=True,
        design_note=design_note,
        weeks=tuple(
            NewProgramWeek(
                week=_week_number(week),
                label=label,
                days=tuple(
                    _build_day(day, day_rows, position=position, exercise_ids=exercise_ids)
                    for position, (day, day_rows) in enumerate(rows_by_day.items(), start=1)
                ),
            )
            for (week, rows_by_day), label in zip(rows_by_week.items(), labels, strict=True)
        ),
    )


def label_weeks(suffixes: Sequence[str]) -> list[str]:
    # ラベルの無い週は、デロードとテストの週を区切りにしてブロックA、B、C と数える
    labels = []
    block = 0
    in_block = False
    for suffix in suffixes:
        if suffix == "":
            labels.append(f"ブロック{chr(ord('A') + block)}")
            in_block = True
            continue
        labels.append(suffix)
        if in_block:
            block += 1
        in_block = False
    return labels


def list_recorded_guide_dates(rows: Iterable[PhaseRow]) -> set[date]:
    return {
        row.guide_date
        for row in rows
        if row.actual_weight is not None or row.actual_reps is not None or row.actual_rir is not None
    }


def list_rir_records(rows: Iterable[PhaseRow]) -> list[RirRecord]:
    return [
        RirRecord(
            date=row.guide_date,
            exercise_name=row.exercise_name,
            weight=row.actual_weight,
            reps=row.actual_reps,
            rir=row.actual_rir,
        )
        for row in rows
        if row.actual_weight is not None and row.actual_reps is not None and row.actual_rir is not None
    ]


def fill_rir(training_logs: Sequence[LegacyTrainingLog], records: Iterable[RirRecord]) -> RirFilling:
    # ponytail: RIR は目安日・種目・重量・回数が一致する最初のセットに限って設定する。
    # 一致しない記録が多ければ、日付の前後1日まで探す範囲を広げる
    logs_by_date = {training_log.date: training_log for training_log in training_logs}
    unfilled_count = 0
    for record in records:
        training_log = logs_by_date.get(record.date)
        filled = None if training_log is None else _fill_first_matching_set(training_log, record)
        if filled is None:
            unfilled_count += 1
            continue
        logs_by_date[record.date] = filled
    return RirFilling(training_logs=tuple(logs_by_date.values()), unfilled_count=unfilled_count)


def validate_bulking_rows(rows: Sequence[PhaseRow]) -> None:
    for row in rows:
        if DAY_PATTERN.fullmatch(row.day) is None:
            raise InvalidLegacyFile(f"増量期シートの Day の列の形式が不正です: 週 {row.week} の {row.day}")
    day_numbers = Counter(
        (_week_number(week), day.partition(" ")[0])
        for week, day in dict.fromkeys((row.week, row.day) for row in rows)
        if not day.startswith(TEST_DAY_PREFIX)
    )
    duplicated_days = [f"週 {week} の {prefix}" for (week, prefix), count in day_numbers.items() if count > 1]
    if len(duplicated_days) > 0:
        raise InvalidLegacyFile(f"増量期シートの週に同じ Day の番号があります: {duplicated_days}")
    week_counts = Counter(_week_number(week) for week in dict.fromkeys(row.week for row in rows))
    duplicated_weeks = [week for week, count in week_counts.items() if count > 1]
    if len(duplicated_weeks) > 0:
        raise InvalidLegacyFile(f"増量期シートの週番号が重複しています: {duplicated_weeks}")
    test_row_counts = Counter(
        (row.week, row.day, row.exercise_name) for row in rows if row.day.startswith(TEST_DAY_PREFIX)
    )
    for (week, day, exercise_name), count in test_row_counts.items():
        if count != len(TEST_WEEK_PERCENTS):
            raise InvalidLegacyFile(
                f"増量期シートのテスト週は種目ごとに{len(TEST_WEEK_PERCENTS)}行にしてください: "
                f"週 {week} の {day} の {exercise_name} は {count} 行です"
            )
    for row in rows:
        guide_date = program_service.calculate_guide_date(
            PROGRAM_START_DATE, week=_week_number(row.week), weekday=WEEKDAYS[row.day.partition(" ")[2]]
        )
        if row.guide_date != guide_date:
            raise InvalidLegacyFile(
                f"増量期シートの目安日が週と曜日から求めた日付と一致しません: "
                f"週 {row.week} の {row.day} は {guide_date} ですが、目安日は {row.guide_date} です"
            )


def validate_training_logs(training_logs: Sequence[LegacyTrainingLog], *, today: date) -> None:
    if len(training_logs) == 0:
        raise InvalidLegacyFile("KINNIK の CSV にトレーニング記録がありません")
    if training_logs[-1].date > today:
        raise InvalidLegacyFile(f"KINNIK の CSV に今日より後の日付があります: {training_logs[-1].date}")
    for training_log in training_logs:
        for exercise in training_log.exercises:
            _validate_api_params(
                SetsReplaceParams,
                {"sets": [asdict(exercise_set) for exercise_set in exercise.sets]},
                reason=(
                    f"KINNIK の CSV のセットが受け付けられる範囲を外れています: {training_log.date} の {exercise.name}"
                ),
            )
            _validate_api_params(
                PerformedExerciseUpdateParams,
                {"memo": exercise.memo},
                reason=(
                    f"KINNIK の CSV のメモが受け付けられる範囲を外れています: {training_log.date} の {exercise.name}"
                ),
            )


def validate_exercise_plans(plans: Iterable[ExerciseToCreate]) -> None:
    for plan in plans:
        _validate_api_params(
            ExerciseSaveParams,
            {
                "name": plan.name,
                "parent_uid": None,
                "coefficient": plan.coefficient,
                "e1rm_divisor": plan.e1rm_divisor,
                "increment_kg": INCREMENT_KG,
                "default_rest_seconds": plan.default_rest_seconds,
            },
            reason=f"種目の値が受け付けられる範囲を外れています: {plan.name}",
        )


def import_legacy_records(
    session: Session, *, training_csv: Path, program_xlsx: Path, maintenance_prompt: Path, today: date
) -> None:
    exercise_repo = get_exercise_repository(session)
    program_repo = get_program_repository(session)
    training_log_repo = get_training_log_repository(session)
    has_exercises = len(exercise_service.list_exercises(exercise_repo)) > 0
    latest = training_log_service.get_latest_training_log(
        training_log_repo, exercise_repo=exercise_repo, program_repo=program_repo
    )
    if has_exercises or latest is not None:
        raise Conflict("種目かトレーニング記録がある DB には移行できません。DB を作り直してから流してください")

    # 書き込みは repository ごとに commit される。途中で失敗して一部だけ残らないよう、
    # 入力の検査を最初の書き込みより前に済ませる
    design_note = extract_design_note(maintenance_prompt.read_text(encoding="utf-8"))
    workbook = load_workbook(program_xlsx, data_only=True)
    bulking_rows = _read_phase_rows(workbook["増量期"])
    validate_bulking_rows(bulking_rows)
    rir_filling = fill_rir(
        parse_training_csv(training_csv.read_text(encoding="utf-8-sig")),
        list_rir_records([*_read_phase_rows(workbook["減量期"]), *bulking_rows]),
    )
    training_logs = rir_filling.training_logs
    validate_training_logs(training_logs, today=today)
    exercise_plans = plan_exercises(
        _read_master_exercises(workbook), training_logs, planned_names=[row.exercise_name for row in bulking_rows]
    )
    validate_exercise_plans(exercise_plans)

    exercises = _create_exercises(exercise_repo, exercise_plans)
    program = program_service.create_program(
        program_repo,
        program=build_program(
            bulking_rows,
            design_note=design_note,
            exercise_ids={name: exercise.id for name, exercise in exercises.items()},
        ),
    )
    recorded_guide_dates = list_recorded_guide_dates(bulking_rows)
    day_uids = {
        program_service.calculate_guide_date(
            program.start_date, week=day_in_week.week.week, weekday=day_in_week.day.weekday
        ): day_in_week.day.uid
        for day_in_week in program_service.list_days_in_order(program)
    }
    for training_log in training_logs:
        _create_training_log(
            training_log_repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            training_log=training_log,
            program_day_uid=day_uids.get(training_log.date) if training_log.date in recorded_guide_dates else None,
            exercises=exercises,
            today=today,
        )

    # 移行後に利用者が入力する TM へ、取り込んだ週の実績で自動の +2.5 が重ならないようにする
    training_log_service.mark_week_evaluated(exercise_repo, on=training_logs[-1].date)

    logger.info("種目 %d 件とプログラム %d 週を取り込みました", len(exercises), len(program.weeks))
    logger.info(
        "トレーニング記録 %d 日、セット %d 件を取り込みました。Day に紐付けた記録は %d 日です",
        len(training_logs),
        sum(len(exercise.sets) for training_log in training_logs for exercise in training_log.exercises),
        sum(1 for training_log in training_logs if training_log.date in recorded_guide_dates),
    )
    logger.info("RIR を入れられなかった xlsx の行は %d 件です", rir_filling.unfilled_count)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="KINNIK の CSV と xlsx から、種目、増量期のプログラム、トレーニング記録を空の DB に取り込む"
    )
    parser.add_argument("--training-csv", type=Path, required=True, help="KINNIK の kinnik_CSV_training_*.csv")
    parser.add_argument("--program-xlsx", type=Path, required=True, help="BIG3プログラム管理.xlsx")
    parser.add_argument("--maintenance-prompt", type=Path, required=True, help="BIG3プログラム管理_保守プロンプト.md")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as session:
        try:
            import_legacy_records(
                session,
                training_csv=args.training_csv,
                program_xlsx=args.program_xlsx,
                maintenance_prompt=args.maintenance_prompt,
                today=get_today(),
            )
        except (Conflict, InvalidLegacyFile) as error:
            logger.error("移行を中断しました。%s", error)
            raise SystemExit(1) from error


def _week_number(week: str) -> int:
    return int(week.partition(" ")[0])


def _validate_api_params(params: type[BaseModel], values: Mapping[str, object], *, reason: str) -> None:
    try:
        params.model_validate(values)
    except ValidationError as error:
        raise InvalidLegacyFile(f"{reason}\n{error}") from error


def _e1rm_divisor(name: str) -> float:
    return BENCH_PRESS_E1RM_DIVISOR if name == BENCH_PRESS else DEFAULT_E1RM_DIVISOR


def _build_day(
    label: str, rows: Sequence[PhaseRow], *, position: int, exercise_ids: Mapping[str, int]
) -> NewProgramDay:
    prefix, _, weekday = label.partition(" ")
    is_test = prefix == TEST_DAY_PREFIX
    occurrences: dict[str, int] = {}
    planned_exercises = []
    for order, row in enumerate(rows, start=1):
        occurrence = occurrences.get(row.exercise_name, 0)
        occurrences[row.exercise_name] = occurrence + 1
        planned_exercises.append(
            NewPlannedExercise(
                exercise_id=exercise_ids[row.exercise_name],
                order=order,
                sets=row.sets,
                reps=row.reps,
                reps_max=None,
                target_rpe=row.target_rpe,
                target_percent=TEST_WEEK_PERCENTS[occurrence] if is_test else None,
            )
        )
    return NewProgramDay(
        day=position if is_test else int(prefix.removeprefix("Day")),
        weekday=WEEKDAYS[weekday],
        planned_exercises=tuple(planned_exercises),
    )


def _fill_first_matching_set(training_log: LegacyTrainingLog, record: RirRecord) -> LegacyTrainingLog | None:
    for exercise_index, exercise in enumerate(training_log.exercises):
        if exercise.name != record.exercise_name:
            continue
        for set_index, exercise_set in enumerate(exercise.sets):
            is_matching = (
                exercise_set.weight == record.weight and exercise_set.reps == record.reps and exercise_set.rir is None
            )
            if not is_matching:
                continue
            sets = list(exercise.sets)
            sets[set_index] = replace(exercise_set, rir=record.rir)
            exercises = list(training_log.exercises)
            exercises[exercise_index] = replace(exercise, sets=tuple(sets))
            return replace(training_log, exercises=tuple(exercises))
    return None


def _read_master_exercises(workbook: Workbook) -> list[MasterExercise]:
    rows = dropwhile(
        lambda row: not str(row[0]).startswith(MASTER_HEADING), workbook["設定"].iter_rows(values_only=True)
    )
    next(rows)
    return [
        MasterExercise(name=row[0].strip(), category=row[1], coefficient=float(row[2]))
        for row in takewhile(lambda row: row[0] is not None, rows)
    ]


def _read_phase_rows(worksheet: Worksheet) -> list[PhaseRow]:
    return [
        PhaseRow(
            week=str(row[0]),
            guide_date=row[1].date(),
            day=str(row[2]),
            exercise_name=row[3].strip(),
            sets=int(row[5]),
            reps=int(row[6]),
            target_rpe=None if row[7] is None else float(row[7]),
            actual_weight=None if row[9] is None else float(row[9]),
            actual_reps=None if row[10] is None else int(row[10]),
            actual_rir=None if row[11] is None else int(row[11]),
        )
        for row in worksheet.iter_rows(min_row=2, values_only=True)
        if any(value is not None for value in row)
    ]


def _create_exercises(repo: ExerciseRepository, plans: Sequence[ExerciseToCreate]) -> dict[str, Exercise]:
    exercises: dict[str, Exercise] = {}
    for plan in plans:
        exercises[plan.name] = exercise_service.create_exercise(
            repo,
            name=plan.name,
            parent_uid=None if plan.parent_name is None else exercises[plan.parent_name].uid,
            coefficient=plan.coefficient,
            e1rm_divisor=plan.e1rm_divisor,
            increment_kg=INCREMENT_KG,
            default_rest_seconds=plan.default_rest_seconds,
        ).exercise
    return exercises


def _create_training_log(
    repo: TrainingLogRepository,
    *,
    exercise_repo: ExerciseRepository,
    program_repo: ProgramRepository,
    training_log: LegacyTrainingLog,
    program_day_uid: str | None,
    exercises: Mapping[str, Exercise],
    today: date,
) -> None:
    created = training_log_service.create_training_log(
        repo,
        exercise_repo=exercise_repo,
        program_repo=program_repo,
        on=training_log.date,
        program_day_uid=program_day_uid,
        today=today,
    ).training_log
    # Day に紐付いた記録は、予定種目ごとにセットが空の実施種目を持って作られる。同じ種目の実施種目へセットを入れ、
    # 予定に無い種目は末尾に追加する
    unfilled = list(created.exercises)
    for legacy_exercise in training_log.exercises:
        exercise = exercises[legacy_exercise.name]
        planned = next((performed for performed in unfilled if performed.exercise_id == exercise.id), None)
        if planned is None:
            detail = training_log_service.add_performed_exercise(
                repo, exercise_repo=exercise_repo, program_repo=program_repo, uid=created.uid, exercise_uid=exercise.uid
            )
            performed_uid = detail.exercises[-1].performed.uid
        else:
            unfilled.remove(planned)
            performed_uid = planned.uid
        training_log_service.replace_sets(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            performed_uid=performed_uid,
            sets=legacy_exercise.sets,
        )
        if legacy_exercise.memo != "":
            training_log_service.update_performed_exercise_memo(
                repo,
                exercise_repo=exercise_repo,
                program_repo=program_repo,
                performed_uid=performed_uid,
                memo=legacy_exercise.memo,
            )


if __name__ == "__main__":
    main()
