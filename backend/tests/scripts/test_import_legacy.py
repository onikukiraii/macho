import csv
import io
import logging
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from common.errors import Conflict
from features.exercise.repository import DbExerciseRepository
from features.exercise.service import create_exercise, is_week_evaluated
from features.exercise.types import TrainingMax, TrainingMaxSource
from features.program.repository import DbProgramRepository
from features.program.types import Program, Weekday
from features.training_log.repository import DbTrainingLogRepository
from features.training_log.service import create_training_log
from features.training_log.types import ExerciseSet, TrainingLog
from scripts.import_legacy import (
    BULKING_PHASE_CSV,
    CUTTING_PHASE_CSV,
    DESIGN_NOTE_MD,
    EXERCISE_MASTER_CSV,
    TRAINING_LOGS_CSV,
    InvalidLegacyFile,
    import_legacy_records,
    main,
    parse_training_csv,
)

TODAY = date(2026, 10, 14)
TRAINING_COLUMNS = ("日付", "種目", "セット", "重量", "レップ数")
MASTER_COLUMNS = ("種目", "区分", "係数")
PHASE_COLUMNS = ("週", "目安日", "Day", "種目", "セット", "レップ", "目標RPE", "実績重量kg", "実績レップ", "実績RIR")
MASTER = [
    ("スクワット", "SQ", 1),
    ("ベンチプレス", "BP", 1),
    ("ポーズベンチ", "BP", 0.87),
    ("デッドリフト", "DL", 1),
    ("ルーマニアンDL", "DL", 0.75),
]
DESIGN_NOTE = "- **構造**: ブロックピリオダイゼーション\n- **デロード**: 主種目セット半減"
TEST_WEEK_REPS = (5, 3, 2, 1, 1, 1)
TEST_WEEK_PERCENTS = [40.0, 60.0, 75.0, 85.0, 92.0, 100.0]


def _training_row(on: str, exercise: str, set_number: int, weight: str, reps: str) -> list[str]:
    return [on, exercise, str(set_number), weight, reps]


def _phase(
    week: str,
    on: str,
    day: str,
    exercise: str,
    *,
    sets: int = 3,
    reps: int = 5,
    rpe: float | None = 7.0,
    actual_weight: float | None = None,
    actual_reps: int | None = None,
    actual_rir: int | None = None,
) -> tuple[object, ...]:
    return (week, on, day, exercise, sets, reps, rpe, actual_weight, actual_reps, actual_rir)


def _write_csv(path: Path, header: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([header, *rows])


def _write_inputs(
    tmp_path: Path,
    *,
    training_rows: list[list[str]],
    bulking_rows: list[tuple[object, ...]],
    cutting_rows: list[tuple[object, ...]] | None = None,
    master: list[tuple[str, str, float]] = MASTER,
) -> None:
    _write_csv(tmp_path / TRAINING_LOGS_CSV, TRAINING_COLUMNS, training_rows)
    _write_csv(tmp_path / EXERCISE_MASTER_CSV, MASTER_COLUMNS, master)
    _write_csv(tmp_path / BULKING_PHASE_CSV, PHASE_COLUMNS, bulking_rows)
    _write_csv(tmp_path / CUTTING_PHASE_CSV, PHASE_COLUMNS, cutting_rows or [])
    (tmp_path / DESIGN_NOTE_MD).write_text(f"{DESIGN_NOTE}\n", encoding="utf-8")


def _import(
    db_session: Session,
    tmp_path: Path,
    *,
    training_rows: list[list[str]],
    bulking_rows: list[tuple[object, ...]],
    cutting_rows: list[tuple[object, ...]] | None = None,
    master: list[tuple[str, str, float]] = MASTER,
) -> None:
    _write_inputs(
        tmp_path, training_rows=training_rows, bulking_rows=bulking_rows, cutting_rows=cutting_rows, master=master
    )
    import_legacy_records(db_session, seed_dir=tmp_path, today=TODAY)


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


class TestImportLegacyRecords:
    def test_training_logs_の全セットが日付ごとの記録になり3つの種目名は対応する名前にまとまる(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        _import(
            db_session,
            tmp_path,
            training_rows=[
                _training_row("2026-09-14", "ベンチプレス", 1, "80", "5"),
                _training_row("2026-09-14", "ベンチプレス", 2, "77.5", "6"),
                _training_row("2026-09-14", "ルーマニアンデッドリフト", 1, "80", "6"),
                _training_row("2026-09-14", "ダンベルカール", 1, "10", "12"),
                _training_row("2026-09-14", "ダンベルカール", 2, "10", "10"),
                _training_row("2026-09-14", "ダンベルカール", 1, "8", "12"),
                _training_row("2026-09-16", "ポーズベンチプレス", 1, "65", "5"),
                _training_row("2026-09-16", "シーテッドレッグプレス", 1, "100", "8"),
            ],
            bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット")],
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

    def test_bulking_phase_が開始日と設計メモ付きのプログラムになり週と_Day_と予定種目が行の順に並ぶ(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        test_days = [("2026-10-19", "テスト 月", "スクワット"), ("2026-10-21", "テスト 水", "ベンチプレス")]
        _import(
            db_session,
            tmp_path,
            training_rows=[_training_row("2026-09-14", "ラットプルダウン", 1, "55", "10")],
            bulking_rows=[
                _phase("1", "2026-09-28", "Day1 月", "スクワット", sets=4, reps=5, rpe=7.5),
                _phase("1", "2026-09-28", "Day1 月", "ラットプルダウン", sets=2, reps=10, rpe=None),
                _phase("1", "2026-10-01", "Day3 木", "ラットプルダウン", sets=3, reps=12, rpe=None),
                _phase("1", "2026-10-01", "Day3 木", "デッドリフト", sets=4, reps=3, rpe=7.5),
                _phase("2 デロード", "2026-10-05", "Day1 月", "スクワット", sets=2, reps=5, rpe=6),
                _phase("3", "2026-10-12", "Day1 月", "ベンチプレス", sets=3, reps=8, rpe=7),
                *[
                    _phase("4 テスト", on, day, exercise, sets=1, reps=reps, rpe=None)
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
                    (3, Weekday.thu, [("ラットプルダウン", 3, 12, None), ("デッドリフト", 4, 3, 7.5)]),
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
        assert [(day.weekday, [p.target_percent for p in day.planned_exercises]) for day in program.weeks[-1].days] == [
            (Weekday.mon, TEST_WEEK_PERCENTS),
            (Weekday.wed, TEST_WEEK_PERCENTS),
            (Weekday.fri, TEST_WEEK_PERCENTS),
        ]
        assert {p.reps_max for week in program.weeks for day in week.days for p in day.planned_exercises} == {None}

    def test_実績のある目安日の記録はその_Day_に紐付きRIR_のある行は一致するセットに入る(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        _import(
            db_session,
            tmp_path,
            training_rows=[
                _training_row("2026-09-14", "ベンチプレス", 1, "80", "5"),
                _training_row("2026-09-14", "ベンチプレス", 2, "80", "5"),
                _training_row("2026-10-01", "デッドリフト", 1, "117.5", "3"),
                _training_row("2026-10-01", "ポーズベンチプレス", 1, "60", "5"),
                _training_row("2026-10-01", "ポーズベンチプレス", 2, "65", "4"),
                _training_row("2026-10-01", "ポーズベンチプレス", 3, "65", "5"),
                _training_row("2026-10-01", "ポーズベンチプレス", 4, "65", "5"),
            ],
            cutting_rows=[
                _phase(
                    "11 (実績のみ)",
                    "2026-09-14",
                    "実績 月",
                    "ベンチプレス",
                    rpe=None,
                    actual_weight=80,
                    actual_reps=5,
                    actual_rir=1,
                ),
            ],
            bulking_rows=[
                _phase("1", "2026-09-28", "Day1 月", "スクワット"),
                _phase("1", "2026-10-01", "Day3 木", "デッドリフト", actual_weight=117.5, actual_reps=3),
                _phase("1", "2026-10-01", "Day3 木", "ポーズベンチ", actual_weight=65, actual_reps=5, actual_rir=2),
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
                ("ポーズベンチ", [(1, 60.0, 5, None), (2, 65.0, 4, None), (3, 65.0, 5, 2), (4, 65.0, 5, None)]),
            ],
        ]

    def test_開始日より前と実績の目安日に一致しない記録は予定外になる(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        _import(
            db_session,
            tmp_path,
            training_rows=[
                _training_row("2026-09-21", "スクワット", 1, "80", "5"),
                _training_row("2026-09-28", "スクワット", 1, "80", "5"),
                _training_row("2026-10-01", "デッドリフト", 1, "117.5", "3"),
                _training_row("2026-10-03", "スクワット", 1, "80", "5"),
            ],
            cutting_rows=[
                _phase(
                    "12 (実績のみ)",
                    "2026-09-21",
                    "実績 月",
                    "スクワット",
                    rpe=None,
                    actual_weight=80,
                    actual_reps=5,
                    actual_rir=2,
                ),
            ],
            bulking_rows=[
                _phase("1", "2026-09-28", "Day1 月", "スクワット"),
                _phase("1", "2026-10-01", "Day3 木", "デッドリフト", actual_weight=117.5, actual_reps=3),
            ],
        )

        program = _program(db_session)
        assert [(training_log.date, training_log.program_day_id) for training_log in _training_logs(db_session)] == [
            (date(2026, 9, 21), None),
            (date(2026, 9, 28), None),
            (date(2026, 10, 1), _day_id(program, week=1, day=3)),
            (date(2026, 10, 3), None),
        ]

    def test_移行のあとで_TM_を入力して新しい週の記録を作っても取り込んだ週の実績で_TM_を上げない(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        _import(
            db_session,
            tmp_path,
            training_rows=[
                _training_row("2026-10-06", "スクワット", 1, "80", "5"),
                _training_row("2026-10-12", "スクワット", 1, "100", "5"),
                _training_row("2026-10-13", "スクワット", 1, "100", "5"),
            ],
            bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット")],
        )
        exercise_repo = DbExerciseRepository(db_session)
        squat_id = next(
            exercise_id for exercise_id, name in _exercise_names(db_session).items() if name == "スクワット"
        )
        exercise_repo.add_training_max(
            TrainingMax(
                exercise_id=squat_id,
                value=100.0,
                effective_at=datetime(2026, 10, 14, 1, 0, tzinfo=UTC),
                source=TrainingMaxSource.manual,
                reason="移行後の入力",
            )
        )

        create_training_log(
            DbTrainingLogRepository(db_session),
            exercise_repo=exercise_repo,
            program_repo=DbProgramRepository(db_session),
            on=date(2026, 10, 19),
            program_day_uid=None,
            today=date(2026, 10, 19),
        )

        assert [training_max.source for training_max in exercise_repo.list_training_maxes()] == [
            TrainingMaxSource.manual
        ]

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
                training_rows=[_training_row("2026-10-01", "スクワット", 1, "80", "5")],
                bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット")],
            )
        exercise_repo = DbExerciseRepository(db_session)
        assert (
            list(_exercise_names(db_session).values()),
            DbProgramRepository(db_session).get_latest(),
            _training_logs(db_session),
            exercise_repo.list_training_maxes(),
            is_week_evaluated(exercise_repo, week_start=date(2026, 9, 28)),
        ) == (["ベンチプレス"], None, [], [], False)

    def test_トレーニング記録だけがある_DB_でも何も書き込まずに中断する(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        existing = create_training_log(
            DbTrainingLogRepository(db_session),
            exercise_repo=DbExerciseRepository(db_session),
            program_repo=DbProgramRepository(db_session),
            on=date(2026, 10, 1),
            program_day_uid=None,
            today=TODAY,
        ).training_log

        with pytest.raises(Conflict, match="種目かトレーニング記録がある DB には移行できません"):
            _import(
                db_session,
                tmp_path,
                training_rows=[_training_row("2026-10-01", "スクワット", 1, "80", "5")],
                bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット")],
            )
        exercise_repo = DbExerciseRepository(db_session)
        assert (
            _exercise_names(db_session),
            DbProgramRepository(db_session).get_latest(),
            _training_logs(db_session),
            exercise_repo.list_training_maxes(),
            is_week_evaluated(exercise_repo, week_start=date(2026, 9, 28)),
        ) == ({}, None, [existing], [], False)

    def test_種目マスタの係数が1以外の種目は本体を派生元にし本体と派生種目のレストを180秒にする(
        self, db_session: Session, tmp_path: Path
    ) -> None:
        _import(
            db_session,
            tmp_path,
            training_rows=[_training_row("2026-09-14", "ラットプルダウン", 1, "55", "10")],
            bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット")],
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

    def test_記録の無い予定種目も補助種目として作る(self, db_session: Session, tmp_path: Path) -> None:
        _import(
            db_session,
            tmp_path,
            training_rows=[_training_row("2026-09-14", "スクワット", 1, "80", "5")],
            bulking_rows=[
                _phase("1", "2026-09-28", "Day1 月", "スクワット"),
                _phase("1", "2026-09-28", "Day1 月", "フェイスプル", rpe=None),
            ],
        )

        assert {
            exercise.name: (exercise.parent_id, exercise.e1rm_divisor, exercise.default_rest_seconds)
            for exercise in DbExerciseRepository(db_session).list_all()
            if exercise.name == "フェイスプル"
        } == {"フェイスプル": (None, 33.3, 90)}

    def test_種目マスタにも_CSV_にも無い予定の種目名は作る前に警告する(
        self, db_session: Session, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.WARNING)

        _import(
            db_session,
            tmp_path,
            training_rows=[_training_row("2026-09-14", "ラットプルダウン", 1, "55", "10")],
            bulking_rows=[
                _phase("1", "2026-09-28", "Day1 月", "スクワット"),
                _phase("1", "2026-09-28", "Day1 月", "ラットプルダウン"),
                _phase("1", "2026-09-28", "Day1 月", "ラットプル"),
            ],
        )

        warnings = [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]
        assert [message.partition(": ")[2] for message in warnings] == ["['ラットプル']"]

    @pytest.mark.parametrize(
        ("training_rows", "bulking_rows", "master", "reason"),
        [
            pytest.param(
                [_training_row("2026-10-01", "スクワット", 1, "80", "5")],
                [_phase("1", "2026-09-28", "Day1月", "スクワット")],
                MASTER,
                "bulking_phase.csv の Day の列の形式が不正です",
                id="Day の列に曜日が無い",
            ),
            pytest.param(
                [_training_row("2026-10-01", "スクワット", 1, "80", "5")],
                [
                    _phase("1", "2026-09-28", "Day1 月", "スクワット"),
                    *[_phase("2 テスト", "2026-10-05", "テスト 月", "スクワット") for _ in range(5)],
                ],
                MASTER,
                "bulking_phase.csv のテスト週は種目ごとに6行にしてください",
                id="テスト週の行が足りない",
            ),
            pytest.param(
                [_training_row("2026-10-01", "スクワット", 1, "80", "5")],
                [
                    _phase("1", "2026-09-28", "Day1 月", "スクワット"),
                    _phase("1 デロード", "2026-09-29", "Day2 火", "ベンチプレス"),
                ],
                MASTER,
                "bulking_phase.csv の週番号が重複しています",
                id="週番号が重複する",
            ),
            pytest.param(
                [_training_row("2026-10-01", "スクワット", 1, "80", "5")],
                [
                    _phase("1", "2026-09-28", "Day1 月", "スクワット"),
                    _phase("1", "2026-09-29", "Day1 火", "ベンチプレス"),
                ],
                MASTER,
                "bulking_phase.csv の週に同じ Day の番号があります",
                id="同じ週の Day の番号が重複する",
            ),
            pytest.param(
                [],
                [_phase("1", "2026-09-28", "Day1 月", "スクワット")],
                MASTER,
                "training_logs.csv にトレーニング記録がありません",
                id="CSV に記録が無い",
            ),
            pytest.param(
                [_training_row("2026-10-15", "スクワット", 1, "80", "5")],
                [_phase("1", "2026-09-28", "Day1 月", "スクワット")],
                MASTER,
                "training_logs.csv に今日より後の日付があります",
                id="CSV に今日より後の日付がある",
            ),
            pytest.param(
                [_training_row("2026-10-01", "スクワット", 1, "80", "5")],
                [_phase("1", "2026-09-29", "Day1 月", "スクワット")],
                MASTER,
                "bulking_phase.csv の目安日が週と曜日から求めた日付と一致しません",
                id="目安日が週と曜日に合わない",
            ),
            pytest.param(
                [_training_row("2026-10-01", "スクワット", 51, "80", "5")],
                [_phase("1", "2026-09-28", "Day1 月", "スクワット")],
                MASTER,
                "training_logs.csv のセットが受け付けられる範囲を外れています",
                id="セット番号が50を超える",
            ),
            pytest.param(
                [_training_row("2026-10-01", "スクワット", 1, "500.5", "5")],
                [_phase("1", "2026-09-28", "Day1 月", "スクワット")],
                MASTER,
                "training_logs.csv のセットが受け付けられる範囲を外れています",
                id="重量が500kgを超える",
            ),
            pytest.param(
                [_training_row("2026-10-01", "スクワット", 1, "80", "101")],
                [_phase("1", "2026-09-28", "Day1 月", "スクワット")],
                MASTER,
                "training_logs.csv のセットが受け付けられる範囲を外れています",
                id="回数が100を超える",
            ),
            pytest.param(
                [_training_row("2026-10-01", "ア" * 65, 1, "80", "5")],
                [_phase("1", "2026-09-28", "Day1 月", "スクワット")],
                MASTER,
                "種目の値が受け付けられる範囲を外れています",
                id="種目名が64字を超える",
            ),
            pytest.param(
                [_training_row("2026-10-01", "スクワット", 1, "80", "5")],
                [_phase("1", "2026-09-28", "Day1 月", "スクワット")],
                [*MASTER, ("ラーセンベンチ", "BP", 2.5)],
                "種目の値が受け付けられる範囲を外れています",
                id="換算係数が2を超える",
            ),
        ],
    )
    def test_入力の形式が不正なら何も書き込まずに理由を出して中断する(
        self,
        db_session: Session,
        tmp_path: Path,
        training_rows: list[list[str]],
        bulking_rows: list[tuple[object, ...]],
        master: list[tuple[str, str, float]],
        reason: str,
    ) -> None:
        with pytest.raises(InvalidLegacyFile, match=reason):
            _import(db_session, tmp_path, training_rows=training_rows, bulking_rows=bulking_rows, master=master)
        assert (
            _exercise_names(db_session),
            DbProgramRepository(db_session).get_latest(),
            _training_logs(db_session),
        ) == (
            {},
            None,
            [],
        )


class TestParseTrainingCsv:
    @pytest.mark.parametrize(
        ("weight", "reps", "expected"),
        [
            ("", "5", ExerciseSet(order=1, weight=0.0, reps=5, rir=None)),
            ("60", "6.5", ExerciseSet(order=1, weight=60.0, reps=7, rir=None)),
            ("60", "7.8367555", ExerciseSet(order=1, weight=60.0, reps=8, rir=None)),
            ("60", "0.4", ExerciseSet(order=1, weight=60.0, reps=0, rir=None)),
        ],
    )
    def test_重量の空欄は0kgにし小数の回数は四捨五入する(self, weight: str, reps: str, expected: ExerciseSet) -> None:
        text = io.StringIO()
        csv.writer(text).writerows([TRAINING_COLUMNS, _training_row("2026-10-01", "ダンベルカール", 1, weight, reps)])

        assert parse_training_csv(text.getvalue())[0].exercises[0].sets == (expected,)

    def test_種目名の前後の空白は除いて同じ種目にまとめる(self) -> None:
        text = io.StringIO()
        csv.writer(text).writerows(
            [
                TRAINING_COLUMNS,
                _training_row("2026-10-01", "懸垂 ", 1, "0", "8"),
                _training_row("2026-10-01", "懸垂", 2, "0", "7"),
            ]
        )

        assert [
            (exercise.name, [exercise_set.order for exercise_set in exercise.sets])
            for exercise in parse_training_csv(text.getvalue())[0].exercises
        ] == [("懸垂", [1, 2])]


class TestMain:
    def test_中断したときは理由をログに出して終了コード1で終わる(
        self,
        db_session: Session,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        create_exercise(
            DbExerciseRepository(db_session),
            name="ベンチプレス",
            parent_uid=None,
            coefficient=None,
            e1rm_divisor=40.0,
            increment_kg=2.5,
            default_rest_seconds=180,
        )
        monkeypatch.setattr("scripts.import_legacy.SessionLocal", lambda: db_session)
        _write_inputs(
            tmp_path,
            training_rows=[_training_row("2026-10-01", "スクワット", 1, "80", "5")],
            bulking_rows=[_phase("1", "2026-09-28", "Day1 月", "スクワット")],
        )

        with pytest.raises(SystemExit) as exit_info:
            main(["--seed-dir", str(tmp_path)])
        assert (exit_info.value.code, caplog.messages) == (
            1,
            [
                "移行を中断しました。"
                "種目かトレーニング記録がある DB には移行できません。DB を作り直してから流してください"
            ],
        )
