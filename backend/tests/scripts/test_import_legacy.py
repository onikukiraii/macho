import csv
from datetime import date, datetime
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy.orm import Session

from common.errors import Conflict
from features.exercise.repository import DbExerciseRepository
from features.exercise.service import create_exercise, is_week_evaluated
from features.program.repository import DbProgramRepository
from features.program.types import Program, Weekday
from features.training_log.repository import DbTrainingLogRepository
from features.training_log.service import create_training_log
from features.training_log.types import TrainingLog
from scripts.import_legacy import import_legacy_data

TODAY = date(2026, 10, 14)
KINNIK_HEADER = [
    "ユーザー",
    "日付",
    "部位",
    "種目",
    "グループセット名",
    "グループセッションID",
    "グループセットID",
    "セット",
    "重量",
    "レップ数",
    "RPE/RIR",
    "種別",
    "セットメモ",
    "メモ",
]
PHASE_HEADER = (
    "週",
    "目安日",
    "Day",
    "種目",
    "区分",
    "セット",
    "レップ",
    "目標RPE",
    "目標重量kg",
    "実績重量kg",
    "実績レップ",
    "実績RIR",
    "実績e1RM",
    "前回実績",
    "メモ",
)
MASTER = [
    ("スクワット", "SQ", 1),
    ("ベンチプレス", "BP", 1),
    ("ポーズベンチ", "BP", 0.87),
    ("デッドリフト", "DL", 1),
    ("ルーマニアンDL", "DL", 0.75),
]
DESIGN_NOTE = "- **構造**: ブロックピリオダイゼーション\n- **デロード**: 主種目セット半減"
PROMPT = f"""# 保守プロンプト

## 2. ファイル仕様

- 設定シート

## 3. プログラム設計仕様(意図を壊さないこと)

{DESIGN_NOTE}

## 4. 運用ルール

- 毎回ジムで
"""
TEST_WEEK_REPS = (5, 3, 2, 1, 1, 1)
TEST_WEEK_PERCENTS = [40.0, 60.0, 75.0, 85.0, 92.0, 100.0]


def _kinnik(on: str, exercise: str, set_number: int, weight: str, reps: str, memo: str = "") -> list[str]:
    return ["まーちゃん", on, "胸", exercise, "", "", "", str(set_number), weight, reps, "", "0", "", memo]


def _phase(
    week: str,
    on: str,
    day: str,
    exercise: str,
    category: str,
    *,
    sets: int = 3,
    reps: int = 5,
    rpe: float | None = 7.0,
    actual_weight: float | None = None,
    actual_reps: int | None = None,
    actual_rir: int | None = None,
) -> tuple[object, ...]:
    return (
        week,
        datetime.fromisoformat(on),
        day,
        exercise,
        category,
        sets,
        reps,
        rpe,
        None,
        actual_weight,
        actual_reps,
        actual_rir,
        0,
        "初回",
        None,
    )


def _import(
    db_session: Session,
    tmp_path: Path,
    *,
    kinnik_rows: list[list[str]],
    bulking_rows: list[tuple[object, ...]],
    cutting_rows: list[tuple[object, ...]] | None = None,
) -> None:
    training_csv = tmp_path / "kinnik_CSV_training.csv"
    with training_csv.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows([KINNIK_HEADER, *kinnik_rows])

    workbook = Workbook()
    settings_sheet = workbook.active
    settings_sheet.title = "設定"
    for row in [
        ("BIG3プログラム 設定",),
        (None,),
        ("■ 種目マスタ(係数 = 本体e1RMに対する換算。青字は調整可)",),
        *MASTER,
        (None,),
        ("■ 実績ベストe1RM(本体換算・自動計算) → 設定値の更新判断に使う",),
    ]:
        settings_sheet.append(row)
    for title, rows in [("減量期", cutting_rows or []), ("増量期", bulking_rows)]:
        sheet = workbook.create_sheet(title)
        for phase_row in [PHASE_HEADER, *rows]:
            sheet.append(phase_row)
    program_xlsx = tmp_path / "BIG3プログラム管理.xlsx"
    workbook.save(program_xlsx)

    maintenance_prompt = tmp_path / "BIG3プログラム管理_保守プロンプト.md"
    maintenance_prompt.write_text(PROMPT, encoding="utf-8")

    import_legacy_data(
        db_session,
        training_csv=training_csv,
        program_xlsx=program_xlsx,
        maintenance_prompt=maintenance_prompt,
        today=TODAY,
    )


def _exercise_names(db_session: Session) -> dict[int, str]:
    return {exercise.id: exercise.name for exercise in DbExerciseRepository(db_session).list_all()}


def _training_logs(db_session: Session) -> list[TrainingLog]:
    return DbTrainingLogRepository(db_session).list_on_or_before(TODAY)


def _program(db_session: Session) -> Program:
    program = DbProgramRepository(db_session).get_latest()
    assert program is not None
    return program


def _day_id(program: Program, *, week: int, day: int) -> int:
    return next(d.id for w in program.weeks if w.week == week for d in w.days if d.day == day)


class TestImportLegacyData:
    def test_KINNIK_の全セットが日付ごとの記録になり3つの種目名は対応する名前にまとまる(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        _import(
            db_session,
            tmp_path,
            kinnik_rows=[
                _kinnik("2026-09-14", "ベンチプレス", 1, "80", "5"),
                _kinnik("2026-09-14", "ベンチプレス", 2, "77.5", "6"),
                _kinnik("2026-09-14", "ルーマニアンデッドリフト", 1, "80", "6"),
                _kinnik("2026-09-14", "ダンベルカール", 1, "10", "12"),
                _kinnik("2026-09-14", "ダンベルカール", 2, "10", "10"),
                _kinnik("2026-09-14", "ダンベルカール", 1, "8", "12"),
                _kinnik("2026-09-16", "ポーズベンチプレス", 1, "65", "5"),
                _kinnik("2026-09-16", "シーテッドレッグプレス", 1, "100", "8"),
            ],
            bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット", "SQ")],
        )

        names = _exercise_names(db_session)
        assert [
            (
                training_log.date,
                [
                    (names[performed.exercise_id], [(s.order, s.weight, s.reps) for s in performed.sets])
                    for performed in training_log.exercises
                ],
            )
            for training_log in _training_logs(db_session)
        ] == [
            (
                date(2026, 9, 14),
                [
                    ("ベンチプレス", [(1, 80.0, 5), (2, 77.5, 6)]),
                    ("ルーマニアンDL", [(1, 80.0, 6)]),
                    ("ダンベルカール", [(1, 10.0, 12), (2, 10.0, 10)]),
                    ("ダンベルカール", [(1, 8.0, 12)]),
                ],
            ),
            (date(2026, 9, 16), [("ポーズベンチ", [(1, 65.0, 5)]), ("レッグプレス", [(1, 100.0, 8)])]),
        ]
        assert sorted(names.values()) == sorted(
            [
                "スクワット",
                "ベンチプレス",
                "ポーズベンチ",
                "デッドリフト",
                "ルーマニアンDL",
                "ダンベルカール",
                "レッグプレス",
            ]
        )

    def test_増量期シートが開始日と設計メモ付きのプログラムになり週と_Day_と予定種目がシートの順に並ぶ(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        test_days = [("2026-10-19", "テスト 月", "スクワット"), ("2026-10-21", "テスト 水", "ベンチプレス")]
        _import(
            db_session,
            tmp_path,
            kinnik_rows=[_kinnik("2026-09-14", "ラットプルダウン", 1, "55", "10")],
            bulking_rows=[
                _phase("1", "2026-09-28", "Day1 月", "スクワット", "SQ", sets=4, reps=5, rpe=7.5),
                _phase("1", "2026-09-28", "Day1 月", "ラットプルダウン", "補助", sets=2, reps=10, rpe=None),
                _phase("1", "2026-10-01", "Day3 木", "デッドリフト", "DL", sets=4, reps=3, rpe=7.5),
                _phase("2 デロード", "2026-10-05", "Day1 月", "スクワット", "SQ", sets=2, reps=5, rpe=6),
                _phase("3", "2026-10-12", "Day1 月", "ベンチプレス", "BP", sets=3, reps=8, rpe=7),
                *[
                    _phase("4 テスト", on, day, exercise, "SQ", sets=1, reps=reps, rpe=None)
                    for on, day, exercise in [*test_days, ("2026-10-23", "テスト 金", "デッドリフト")]
                    for reps in TEST_WEEK_REPS
                ],
            ],
        )

        program = _program(db_session)
        names = _exercise_names(db_session)
        assert (program.name, program.start_date, program.tm_auto_update, program.design_note) == (
            "2026 増量期",
            date(2026, 9, 28),
            True,
            DESIGN_NOTE,
        )
        assert [
            (
                week.week,
                week.label,
                [
                    (
                        day.day,
                        day.weekday,
                        [(names[p.exercise_id], p.sets, p.reps, p.target_rpe) for p in day.planned_exercises],
                    )
                    for day in week.days
                ],
            )
            for week in program.weeks
        ] == [
            (
                1,
                "ブロックA",
                [
                    (1, Weekday.mon, [("スクワット", 4, 5, 7.5), ("ラットプルダウン", 2, 10, None)]),
                    (3, Weekday.thu, [("デッドリフト", 4, 3, 7.5)]),
                ],
            ),
            (2, "デロード", [(1, Weekday.mon, [("スクワット", 2, 5, 6.0)])]),
            (3, "ブロックB", [(1, Weekday.mon, [("ベンチプレス", 3, 8, 7.0)])]),
            (
                4,
                "テスト",
                [
                    (day, weekday, [(exercise, 1, reps, None) for reps in TEST_WEEK_REPS])
                    for day, weekday, exercise in [
                        (1, Weekday.mon, "スクワット"),
                        (2, Weekday.wed, "ベンチプレス"),
                        (3, Weekday.fri, "デッドリフト"),
                    ]
                ],
            ),
        ]
        test_week = program.weeks[-1]
        assert (
            [(day.weekday, [p.target_percent for p in day.planned_exercises]) for day in test_week.days],
            {p.reps_max for week in program.weeks for day in week.days for p in day.planned_exercises},
        ) == (
            [
                (Weekday.mon, TEST_WEEK_PERCENTS),
                (Weekday.wed, TEST_WEEK_PERCENTS),
                (Weekday.fri, TEST_WEEK_PERCENTS),
            ],
            {None},
        )

    def test_実績のある目安日の記録はその_Day_に紐付きRIR_のある行は一致するセットに入る(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        _import(
            db_session,
            tmp_path,
            kinnik_rows=[
                _kinnik("2026-09-14", "ベンチプレス", 1, "80", "5"),
                _kinnik("2026-09-14", "ベンチプレス", 2, "80", "5"),
                _kinnik("2026-10-01", "デッドリフト", 1, "117.5", "3"),
                _kinnik("2026-10-01", "ポーズベンチプレス", 1, "60", "5"),
                _kinnik("2026-10-01", "ポーズベンチプレス", 2, "65", "5"),
                _kinnik("2026-10-01", "ポーズベンチプレス", 3, "65", "5"),
            ],
            cutting_rows=[
                _phase(
                    "11 (実績のみ)",
                    "2026-09-14",
                    "実績 月",
                    "ベンチプレス",
                    "BP",
                    rpe=None,
                    actual_weight=80,
                    actual_reps=5,
                    actual_rir=1,
                ),
            ],
            bulking_rows=[
                _phase("1", "2026-09-28", "Day1 月", "スクワット", "SQ"),
                _phase("1", "2026-10-01", "Day3 木", "デッドリフト", "DL", actual_weight=117.5, actual_reps=3),
                _phase(
                    "1", "2026-10-01", "Day3 木", "ポーズベンチ", "BP", actual_weight=65, actual_reps=5, actual_rir=2
                ),
            ],
        )

        program = _program(db_session)
        names = _exercise_names(db_session)
        training_logs = _training_logs(db_session)
        assert [(training_log.date, training_log.program_day_id) for training_log in training_logs] == [
            (date(2026, 9, 14), None),
            (date(2026, 10, 1), _day_id(program, week=1, day=3)),
        ]
        assert [
            [
                (names[performed.exercise_id], [(s.order, s.weight, s.reps, s.rir) for s in performed.sets])
                for performed in training_log.exercises
            ]
            for training_log in training_logs
        ] == [
            [("ベンチプレス", [(1, 80.0, 5, 1), (2, 80.0, 5, None)])],
            [
                ("デッドリフト", [(1, 117.5, 3, None)]),
                ("ポーズベンチ", [(1, 60.0, 5, None), (2, 65.0, 5, 2), (3, 65.0, 5, None)]),
            ],
        ]

    def test_開始日より前と実績の目安日に一致しない記録は予定外になる(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        _import(
            db_session,
            tmp_path,
            kinnik_rows=[
                _kinnik("2026-09-21", "スクワット", 1, "80", "5"),
                _kinnik("2026-09-28", "スクワット", 1, "80", "5"),
                _kinnik("2026-10-01", "デッドリフト", 1, "117.5", "3"),
                _kinnik("2026-10-03", "スクワット", 1, "80", "5"),
            ],
            bulking_rows=[
                _phase("1", "2026-09-28", "Day1 月", "スクワット", "SQ"),
                _phase("1", "2026-10-01", "Day3 木", "デッドリフト", "DL", actual_weight=117.5, actual_reps=3),
            ],
        )

        program = _program(db_session)
        assert [(training_log.date, training_log.program_day_id) for training_log in _training_logs(db_session)] == [
            (date(2026, 9, 21), None),
            (date(2026, 9, 28), None),
            (date(2026, 10, 1), _day_id(program, week=1, day=3)),
            (date(2026, 10, 3), None),
        ]

    def test_取り込んだ最も新しい記録の週を評価済みにする(self, db_session: Session, tmp_path: Path) -> None:
        _import(
            db_session,
            tmp_path,
            kinnik_rows=[
                _kinnik("2026-10-01", "スクワット", 1, "80", "5"),
                _kinnik("2026-10-06", "スクワット", 1, "80", "5"),
                _kinnik("2026-10-07", "スクワット", 1, "80", "5"),
            ],
            bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット", "SQ")],
        )

        assert is_week_evaluated(DbExerciseRepository(db_session), week_start=date(2026, 10, 5)) is True

    def test_種目がある_DB_では何も書き込まずに中断する(self, db_session: Session, tmp_path: Path) -> None:
        exercise_repo = DbExerciseRepository(db_session)
        create_exercise(
            exercise_repo,
            name="ベンチプレス",
            parent_uid=None,
            coefficient=None,
            e1rm_divisor=40.0,
            increment_kg=2.5,
            default_rest_seconds=180,
        )

        with pytest.raises(Conflict, match="種目かトレーニング記録がある DB には移行できません"):
            _import(
                db_session,
                tmp_path,
                kinnik_rows=[_kinnik("2026-10-01", "スクワット", 1, "80", "5")],
                bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット", "SQ")],
            )
        assert (
            list(_exercise_names(db_session).values()),
            DbProgramRepository(db_session).get_latest(),
            _training_logs(db_session),
        ) == (["ベンチプレス"], None, [])

    def test_トレーニング記録だけがある_DB_でも中断する(self, db_session: Session, tmp_path: Path) -> None:
        create_training_log(
            DbTrainingLogRepository(db_session),
            exercise_repo=DbExerciseRepository(db_session),
            program_repo=DbProgramRepository(db_session),
            on=date(2026, 10, 1),
            program_day_uid=None,
            today=TODAY,
        )

        with pytest.raises(Conflict, match="種目かトレーニング記録がある DB には移行できません"):
            _import(
                db_session,
                tmp_path,
                kinnik_rows=[_kinnik("2026-10-01", "スクワット", 1, "80", "5")],
                bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット", "SQ")],
            )

    def test_種目マスタの係数が1以外の種目は本体を派生元にし本体と派生種目のレストを180秒にする(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        _import(
            db_session,
            tmp_path,
            kinnik_rows=[_kinnik("2026-09-14", "ラットプルダウン", 1, "55", "10")],
            bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット", "SQ")],
        )

        names = _exercise_names(db_session)
        assert {
            exercise.name: (
                None if exercise.parent_id is None else names[exercise.parent_id],
                exercise.coefficient,
                exercise.e1rm_divisor,
                exercise.increment_kg,
                exercise.default_rest_seconds,
            )
            for exercise in DbExerciseRepository(db_session).list_all()
        } == {
            "スクワット": (None, None, 33.3, 2.5, 180),
            "ベンチプレス": (None, None, 40.0, 2.5, 180),
            "ポーズベンチ": ("ベンチプレス", 0.87, None, 2.5, 180),
            "デッドリフト": (None, None, 33.3, 2.5, 180),
            "ルーマニアンDL": ("デッドリフト", 0.75, None, 2.5, 180),
            "ラットプルダウン": (None, None, 33.3, 2.5, 90),
        }
