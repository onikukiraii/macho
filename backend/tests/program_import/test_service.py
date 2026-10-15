from datetime import date

import pytest
from sqlalchemy.orm import Session

from common.errors import BusinessRuleViolation
from features.exercise.repository import DbExerciseRepository
from features.exercise.service import add_training_max, create_exercise, list_exercises
from features.exercise.types import BodyPart
from features.program.repository import DbProgramRepository
from features.program.service import create_program, get_current_program
from features.program.types import NewPlannedExercise, NewProgram, NewProgramDay, NewProgramWeek, Weekday
from features.program_import.service import import_program, preview_program
from features.program_import.types import (
    DraftDay,
    DraftExercise,
    DraftPlannedExercise,
    DraftWeek,
    ProgramDraft,
    ProgramPreview,
)
from features.training_log.repository import DbTrainingLogRepository
from features.training_log.service import get_day_options

TODAY = date(2026, 10, 19)


@pytest.fixture()
def exercise_repo(db_session: Session) -> DbExerciseRepository:
    repo = DbExerciseRepository(db_session)
    bench = create_exercise(
        repo,
        name="ベンチプレス",
        body_part=BodyPart.chest,
        parent_uid=None,
        coefficient=None,
        e1rm_divisor=40.0,
        increment_kg=2.5,
        default_rest_seconds=180,
    )
    add_training_max(repo, uid=bench.exercise.uid, value=90.5, reason="初期値")
    return repo


@pytest.fixture()
def program_repo(db_session: Session, exercise_repo: DbExerciseRepository) -> DbProgramRepository:
    repo = DbProgramRepository(db_session)
    bench_id = _exercise_id(exercise_repo, "ベンチプレス")
    create_program(
        repo,
        program=NewProgram(
            name="2026 増量期",
            start_date=date(2026, 9, 28),
            tm_auto_update=True,
            design_note="",
            weeks=(
                NewProgramWeek(
                    week=1,
                    label="ブロックA",
                    days=(
                        NewProgramDay(
                            day=1,
                            weekday=Weekday.mon,
                            planned_exercises=(
                                NewPlannedExercise(
                                    exercise_id=bench_id,
                                    order=1,
                                    sets=4,
                                    reps=5,
                                    reps_max=None,
                                    target_rpe=7.5,
                                    target_percent=None,
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    return repo


@pytest.fixture()
def training_log_repo(db_session: Session) -> DbTrainingLogRepository:
    return DbTrainingLogRepository(db_session)


def _exercise_id(exercise_repo: DbExerciseRepository, name: str) -> int:
    return next(e.exercise.id for e in list_exercises(exercise_repo) if e.exercise.name == name)


def _planned(
    name: str, *, reps: int, target_rpe: float | None = None, target_percent: float | None = None
) -> DraftPlannedExercise:
    return DraftPlannedExercise(
        exercise_name=name, sets=3, reps=reps, reps_max=None, target_rpe=target_rpe, target_percent=target_percent
    )


LARSEN_BENCH = DraftExercise(
    name="ラーセンベンチ",
    body_part=BodyPart.chest,
    parent_name="ベンチプレス",
    coefficient=0.85,
    e1rm_divisor=None,
    increment_kg=2.5,
    default_rest_seconds=180,
)
DRAFT = ProgramDraft(
    name="ベンチ スモロフ Jr",
    start_date=date(2026, 10, 19),
    tm_auto_update=False,
    design_note="増量期の第4週から",
    new_exercises=(LARSEN_BENCH,),
    weeks=(
        DraftWeek(
            week=1,
            label="導入",
            days=(
                DraftDay(day=1, weekday=Weekday.mon, exercises=(_planned("ベンチプレス", reps=6, target_percent=70),)),
                DraftDay(
                    day=2,
                    weekday=Weekday.tue,
                    exercises=(
                        _planned("ベンチプレス", reps=5, target_percent=75),
                        _planned("ラーセンベンチ", reps=8, target_rpe=7),
                    ),
                ),
            ),
        ),
        DraftWeek(
            week=2,
            label="導入",
            days=(
                DraftDay(
                    day=1, weekday=Weekday.mon, exercises=(_planned("ベンチプレス", reps=6, target_percent=72.5),)
                ),
            ),
        ),
    ),
)
INVALID_DRAFT = ProgramDraft(
    name="壊れたプログラム",
    start_date=date(2026, 10, 19),
    tm_auto_update=False,
    design_note="",
    new_exercises=(LARSEN_BENCH,),
    weeks=(
        DraftWeek(
            week=1,
            label="導入",
            days=(DraftDay(day=1, weekday=Weekday.mon, exercises=(_planned("デッドリフト", reps=5, target_rpe=8),)),),
        ),
    ),
)


def _preview(
    program_repo: DbProgramRepository, exercise_repo: DbExerciseRepository, training_log_repo: DbTrainingLogRepository
) -> ProgramPreview:
    result = preview_program(
        program_repo=program_repo,
        exercise_repo=exercise_repo,
        training_log_repo=training_log_repo,
        draft=DRAFT,
        today=TODAY,
    )
    assert isinstance(result, ProgramPreview)
    return result


class TestPreviewProgram:
    def test_正しい下書きは週と_Day_と予定種目の並びでプレビューになる(
        self,
        program_repo: DbProgramRepository,
        exercise_repo: DbExerciseRepository,
        training_log_repo: DbTrainingLogRepository,
    ) -> None:
        preview = _preview(program_repo, exercise_repo, training_log_repo)

        assert [
            (week.week, [(day.day, [planned.planned.exercise_name for planned in day.exercises]) for day in week.days])
            for week in preview.weeks
        ] == [(1, [(1, ["ベンチプレス"]), (2, ["ベンチプレス", "ラーセンベンチ"])]), (2, [(1, ["ベンチプレス"])])]

    def test_新しい派生種目は新規と分かり親のトレーニングマックスと換算係数から目標重量を出す(
        self,
        program_repo: DbProgramRepository,
        exercise_repo: DbExerciseRepository,
        training_log_repo: DbTrainingLogRepository,
    ) -> None:
        larsen = _preview(program_repo, exercise_repo, training_log_repo).weeks[0].days[1].exercises[1]

        assert (larsen.is_new_exercise, larsen.target_weight) == (True, 60.0)


class TestImportProgram:
    def test_新しい種目を親の派生種目として作る(
        self,
        program_repo: DbProgramRepository,
        exercise_repo: DbExerciseRepository,
        training_log_repo: DbTrainingLogRepository,
    ) -> None:
        import_program(
            program_repo=program_repo,
            exercise_repo=exercise_repo,
            training_log_repo=training_log_repo,
            draft=DRAFT,
            today=TODAY,
        )

        larsen = next(e for e in list_exercises(exercise_repo) if e.exercise.name == "ラーセンベンチ")
        assert (larsen.exercise.parent_id, larsen.exercise.coefficient) == (
            _exercise_id(exercise_repo, "ベンチプレス"),
            0.85,
        )

    def test_既存のプログラムより開始日が後なので追加したプログラムが進行中になる(
        self,
        program_repo: DbProgramRepository,
        exercise_repo: DbExerciseRepository,
        training_log_repo: DbTrainingLogRepository,
    ) -> None:
        program = import_program(
            program_repo=program_repo,
            exercise_repo=exercise_repo,
            training_log_repo=training_log_repo,
            draft=DRAFT,
            today=TODAY,
        )

        current = get_current_program(program_repo)
        assert current is not None
        assert current.uid == program.uid

    def test_追加したプログラムの次の_Day_は第1週_Day_1(
        self,
        program_repo: DbProgramRepository,
        exercise_repo: DbExerciseRepository,
        training_log_repo: DbTrainingLogRepository,
    ) -> None:
        import_program(
            program_repo=program_repo,
            exercise_repo=exercise_repo,
            training_log_repo=training_log_repo,
            draft=DRAFT,
            today=TODAY,
        )

        options = get_day_options(training_log_repo, program_repo=program_repo)
        next_day = next(option.scheduled_day for option in options if option.is_next)
        assert (next_day.week.week, next_day.day.day) == (1, 1)

    def test_下書きの週と_Day_と予定種目を新しい種目に紐付けて保存する(
        self,
        program_repo: DbProgramRepository,
        exercise_repo: DbExerciseRepository,
        training_log_repo: DbTrainingLogRepository,
    ) -> None:
        program = import_program(
            program_repo=program_repo,
            exercise_repo=exercise_repo,
            training_log_repo=training_log_repo,
            draft=DRAFT,
            today=TODAY,
        )

        bench_id = _exercise_id(exercise_repo, "ベンチプレス")
        larsen_id = _exercise_id(exercise_repo, "ラーセンベンチ")
        assert (
            program.start_date,
            program.tm_auto_update,
            program.design_note,
            [
                (
                    week.week,
                    [
                        (
                            day.day,
                            [
                                (p.exercise_id, p.order, p.reps, p.target_rpe, p.target_percent)
                                for p in day.planned_exercises
                            ],
                        )
                        for day in week.days
                    ],
                )
                for week in program.weeks
            ],
        ) == (
            date(2026, 10, 19),
            False,
            "増量期の第4週から",
            [
                (
                    1,
                    [
                        (1, [(bench_id, 1, 6, None, 70.0)]),
                        (2, [(bench_id, 1, 5, None, 75.0), (larsen_id, 2, 8, 7.0, None)]),
                    ],
                ),
                (2, [(1, [(bench_id, 1, 6, None, 72.5)])]),
            ],
        )

    def test_下書きに検証エラーがあれば種目もプログラムも作らない(
        self,
        program_repo: DbProgramRepository,
        exercise_repo: DbExerciseRepository,
        training_log_repo: DbTrainingLogRepository,
    ) -> None:
        with pytest.raises(BusinessRuleViolation):
            import_program(
                program_repo=program_repo,
                exercise_repo=exercise_repo,
                training_log_repo=training_log_repo,
                draft=INVALID_DRAFT,
                today=TODAY,
            )

        current = get_current_program(program_repo)
        assert (
            [e.exercise.name for e in list_exercises(exercise_repo)],
            current.name if current is not None else None,
        ) == (
            ["ベンチプレス"],
            "2026 増量期",
        )
