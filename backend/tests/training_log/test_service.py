from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.orm import Session

from common.errors import BusinessRuleViolation
from features.exercise.repository import DbExerciseRepository
from features.exercise.service import create_exercise, get_exercise, record_weekly_evaluation
from features.exercise.types import ResolvedExercise, TrainingMax, TrainingMaxSource
from features.program.repository import DbProgramRepository
from features.program.service import create_program
from features.program.types import NewPlannedExercise, NewProgram, NewProgramDay, NewProgramWeek, Program, Weekday
from features.training_log.repository import DbTrainingLogRepository
from features.training_log.service import (
    add_performed_exercise,
    create_training_log,
    delete_training_log,
    get_day_options,
    get_training_log,
    list_exercise_history,
    list_training_logs,
    replace_sets,
    update_performed_exercise,
)
from features.training_log.types import ExerciseSet, PreviousResult, TrainingLogCreated

PROGRAM_START = date(2026, 9, 28)
WEEKDAYS = (Weekday.mon, Weekday.tue, Weekday.thu, Weekday.fri)


@pytest.fixture()
def repo(db_session: Session) -> DbTrainingLogRepository:
    return DbTrainingLogRepository(db_session)


@pytest.fixture()
def exercise_repo(db_session: Session) -> DbExerciseRepository:
    return DbExerciseRepository(db_session)


@pytest.fixture()
def program_repo(db_session: Session) -> DbProgramRepository:
    return DbProgramRepository(db_session)


def _exercise(
    exercise_repo: DbExerciseRepository,
    name: str,
    *,
    e1rm_divisor: float | None = 40.0,
    parent: ResolvedExercise | None = None,
    coefficient: float | None = None,
) -> ResolvedExercise:
    return create_exercise(
        exercise_repo,
        name=name,
        parent_uid=None if parent is None else parent.exercise.uid,
        coefficient=coefficient,
        e1rm_divisor=e1rm_divisor,
        increment_kg=2.5,
        default_rest_seconds=180,
    )


def _set_training_max(exercise_repo: DbExerciseRepository, exercise: ResolvedExercise, value: float) -> None:
    exercise_repo.add_training_max(
        TrainingMax(
            exercise_id=exercise.exercise.id,
            value=value,
            effective_at=datetime(2026, 9, 1, tzinfo=UTC),
            source=TrainingMaxSource.manual,
            reason="入力",
        )
    )


def _planned(exercise: ResolvedExercise, *, order: int, sets: int = 3, target_rpe: float = 7.5) -> NewPlannedExercise:
    return NewPlannedExercise(
        exercise_id=exercise.exercise.id,
        order=order,
        sets=sets,
        reps=5,
        reps_max=None,
        target_rpe=target_rpe,
        target_percent=None,
    )


def _program(
    program_repo: DbProgramRepository,
    *,
    planned: tuple[NewPlannedExercise, ...],
    week_count: int = 3,
    tm_auto_update: bool = True,
) -> Program:
    return create_program(
        program_repo,
        program=NewProgram(
            name="2026 増量期",
            start_date=PROGRAM_START,
            tm_auto_update=tm_auto_update,
            design_note="",
            weeks=tuple(
                NewProgramWeek(
                    week=week,
                    label="ブロックA",
                    days=tuple(
                        NewProgramDay(day=day, weekday=weekday, planned_exercises=planned)
                        for day, weekday in enumerate(WEEKDAYS, start=1)
                    ),
                )
                for week in range(1, week_count + 1)
            ),
        ),
    )


def _day_uid(program: Program, *, week: int, day: int) -> str:
    return program.weeks[week - 1].days[day - 1].uid


def _record(
    repo: DbTrainingLogRepository,
    exercise_repo: DbExerciseRepository,
    program_repo: DbProgramRepository,
    *,
    on: date,
    sets_by_exercise: list[tuple[ResolvedExercise, list[ExerciseSet]]],
    program_day_uid: str | None = None,
) -> TrainingLogCreated:
    created = create_training_log(
        repo, exercise_repo=exercise_repo, program_repo=program_repo, on=on, program_day_uid=program_day_uid, today=on
    )
    for exercise, sets in sets_by_exercise:
        detail = add_performed_exercise(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            uid=created.training_log.uid,
            exercise_uid=exercise.exercise.uid,
        )
        replace_sets(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            performed_uid=detail.exercises[-1].performed.uid,
            sets=sets,
        )
    return created


class TestGetDayOptions:
    def test_次の_Day_の週の全_Day_と最後に記録した_Day_が並び同じ_Day_を記録しても次は変わらない(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        program = _program(program_repo, planned=(_planned(bench, order=1),))
        recorded_dates = [date(2026, 9, 28), date(2026, 9, 29), date(2026, 10, 1), date(2026, 10, 2)]
        recorded_dates += [date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 8), date(2026, 10, 9)]
        for index, on in enumerate(recorded_dates):
            day_uid = _day_uid(program, week=index // 4 + 1, day=index % 4 + 1)
            _record(repo, exercise_repo, program_repo, on=on, sets_by_exercise=[], program_day_uid=day_uid)

        options = get_day_options(repo, program_repo=program_repo)

        assert [
            (option.scheduled_day.week.week, option.scheduled_day.day.day, option.is_next, option.last_recorded_on)
            for option in options
        ] == [
            (3, 1, True, None),
            (3, 2, False, None),
            (3, 3, False, None),
            (3, 4, False, None),
            (2, 4, False, date(2026, 10, 9)),
        ]

        _record(
            repo,
            exercise_repo,
            program_repo,
            on=date(2026, 10, 12),
            sets_by_exercise=[],
            program_day_uid=_day_uid(program, week=2, day=4),
        )
        options = get_day_options(repo, program_repo=program_repo)

        assert [
            (option.scheduled_day.week.week, option.scheduled_day.day.day, option.is_next, option.last_recorded_on)
            for option in options
        ] == [
            (3, 1, True, None),
            (3, 2, False, None),
            (3, 3, False, None),
            (3, 4, False, None),
            (2, 4, False, date(2026, 10, 12)),
        ]


class TestCreateTrainingLog:
    def test_Day_を選ぶと予定種目が予定の順に空のセットで並ぶ(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        squat = _exercise(exercise_repo, "スクワット", e1rm_divisor=33.3)
        program = _program(program_repo, planned=(_planned(bench, order=2, sets=3), _planned(squat, order=1, sets=4)))

        created = create_training_log(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            on=date(2026, 10, 12),
            program_day_uid=_day_uid(program, week=3, day=1),
            today=date(2026, 10, 12),
        )
        detail = get_training_log(
            repo, exercise_repo=exercise_repo, program_repo=program_repo, uid=created.training_log.uid
        )

        assert [
            (
                performed.exercise.name,
                None if performed.planned is None else performed.planned.sets,
                performed.performed.sets,
            )
            for performed in detail.exercises
        ] == [("スクワット", 4, ()), ("ベンチプレス", 3, ())]

    def test_予定外のトレーニングは種目の無い記録になり追加した種目は末尾に並ぶ(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        squat = _exercise(exercise_repo, "スクワット", e1rm_divisor=33.3)

        created = create_training_log(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            on=date(2026, 10, 12),
            program_day_uid=None,
            today=date(2026, 10, 12),
        )
        for exercise in (bench, squat):
            detail = add_performed_exercise(
                repo,
                exercise_repo=exercise_repo,
                program_repo=program_repo,
                uid=created.training_log.uid,
                exercise_uid=exercise.exercise.uid,
            )

        assert (
            created.training_log.exercises,
            [performed.exercise.name for performed in detail.exercises],
        ) == ((), ["ベンチプレス", "スクワット"])

    @pytest.mark.parametrize(
        ("on", "expectation"),
        [
            pytest.param(
                date(2026, 10, 15),
                pytest.raises(BusinessRuleViolation, match="^未来の日付ではトレーニング記録を作成できません$"),
                id="明日",
            ),
            pytest.param(date(2026, 10, 14), nullcontext(), id="今日"),
        ],
    )
    def test_今日より後の日付では作成できない(
        self,
        repo: DbTrainingLogRepository,
        exercise_repo: DbExerciseRepository,
        program_repo: DbProgramRepository,
        on: date,
        expectation: AbstractContextManager[object],
    ) -> None:
        with expectation:
            create_training_log(
                repo,
                exercise_repo=exercise_repo,
                program_repo=program_repo,
                on=on,
                program_day_uid=None,
                today=date(2026, 10, 14),
            )

    def test_前の週に_TM_に_2_5_足した値へ届いていれば新しい週の最初の記録で_TM_を上げる(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        _set_training_max(exercise_repo, bench, 88.0)
        _program(program_repo, planned=())
        _record(
            repo,
            exercise_repo,
            program_repo,
            on=date(2026, 10, 6),
            sets_by_exercise=[(bench, [ExerciseSet(order=1, weight=77.5, reps=5, rir=2)])],
        )

        created = create_training_log(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            on=date(2026, 10, 13),
            program_day_uid=None,
            today=date(2026, 10, 13),
        )

        latest = get_exercise(exercise_repo, uid=bench.exercise.uid).training_max_history[0]
        assert [(update.exercise_name, update.before, update.after) for update in created.training_max_updates] == [
            ("ベンチプレス", 88.0, 90.5)
        ]
        assert (latest.value, latest.source) == (90.5, TrainingMaxSource.auto)

    def test_前の週に複数の種目が届いていればすべての種目の_TM_を上げる(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        squat = _exercise(exercise_repo, "スクワット", e1rm_divisor=33.3)
        _set_training_max(exercise_repo, bench, 88.0)
        _set_training_max(exercise_repo, squat, 125.0)
        _program(program_repo, planned=())
        _record(
            repo,
            exercise_repo,
            program_repo,
            on=date(2026, 10, 6),
            sets_by_exercise=[
                (bench, [ExerciseSet(order=1, weight=77.5, reps=5, rir=2)]),
                (squat, [ExerciseSet(order=1, weight=110.0, reps=5, rir=2)]),
            ],
        )

        created = create_training_log(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            on=date(2026, 10, 13),
            program_day_uid=None,
            today=date(2026, 10, 13),
        )

        assert [(update.exercise_name, update.before, update.after) for update in created.training_max_updates] == [
            ("ベンチプレス", 88.0, 90.5),
            ("スクワット", 125.0, 127.5),
        ]

    def test_最も新しい記録が2週前なら2週前の週を判定する(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        _set_training_max(exercise_repo, bench, 88.0)
        _program(program_repo, planned=())
        _record(
            repo,
            exercise_repo,
            program_repo,
            on=date(2026, 9, 29),
            sets_by_exercise=[(bench, [ExerciseSet(order=1, weight=77.5, reps=5, rir=2)])],
        )

        created = create_training_log(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            on=date(2026, 10, 13),
            program_day_uid=None,
            today=date(2026, 10, 13),
        )

        assert [(update.exercise_name, update.before, update.after) for update in created.training_max_updates] == [
            ("ベンチプレス", 88.0, 90.5)
        ]

    def test_新しい週の最初の記録を削除して作り直しても_TM_は1回しか上がらない(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        _set_training_max(exercise_repo, bench, 88.0)
        _program(program_repo, planned=())
        _record(
            repo,
            exercise_repo,
            program_repo,
            on=date(2026, 10, 6),
            sets_by_exercise=[(bench, [ExerciseSet(order=1, weight=77.5, reps=5, rir=2)])],
        )
        first = _record(repo, exercise_repo, program_repo, on=date(2026, 10, 13), sets_by_exercise=[])
        delete_training_log(repo, uid=first.training_log.uid)

        _record(repo, exercise_repo, program_repo, on=date(2026, 10, 13), sets_by_exercise=[])

        history = get_exercise(exercise_repo, uid=bench.exercise.uid).training_max_history
        assert [training_max.value for training_max in history] == [90.5, 88.0]

    @pytest.mark.parametrize(
        ("tm_auto_update", "existing_on", "new_on"),
        [
            pytest.param(True, date(2026, 10, 6), date(2026, 10, 8), id="同じ週の2件目"),
            pytest.param(True, date(2026, 10, 13), date(2026, 10, 6), id="最も新しい記録より前の日付"),
            pytest.param(False, date(2026, 10, 6), date(2026, 10, 13), id="TM_の自動更新が無効なプログラム"),
        ],
    )
    def test_判定の対象にならない記録では_TM_を上げない(
        self,
        repo: DbTrainingLogRepository,
        exercise_repo: DbExerciseRepository,
        program_repo: DbProgramRepository,
        tm_auto_update: bool,
        existing_on: date,
        new_on: date,
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        _set_training_max(exercise_repo, bench, 88.0)
        _program(program_repo, planned=(), tm_auto_update=tm_auto_update)
        _record(
            repo,
            exercise_repo,
            program_repo,
            on=existing_on,
            sets_by_exercise=[(bench, [ExerciseSet(order=1, weight=77.5, reps=5, rir=2)])],
        )

        created = create_training_log(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            on=new_on,
            program_day_uid=None,
            today=date(2026, 10, 13),
        )

        assert created.training_max_updates == ()

    def test_並行した作成で週が評価済みになっていれば評価済みとして記録を作る(
        self, repo: DbTrainingLogRepository, db_session: Session, program_repo: DbProgramRepository
    ) -> None:
        exercise_repo = _EvaluationRacingExerciseRepository(db_session)
        bench = _exercise(exercise_repo, "ベンチプレス")
        _set_training_max(exercise_repo, bench, 88.0)
        _program(program_repo, planned=())
        _record(
            repo,
            exercise_repo,
            program_repo,
            on=date(2026, 10, 6),
            sets_by_exercise=[(bench, [ExerciseSet(order=1, weight=77.5, reps=5, rir=2)])],
        )
        record_weekly_evaluation(exercise_repo, week_start=date(2026, 10, 5), updates=[])

        created = create_training_log(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            on=date(2026, 10, 13),
            program_day_uid=None,
            today=date(2026, 10, 13),
        )

        assert (created.training_max_updates, repo.get(created.training_log.uid).date) == ((), date(2026, 10, 13))


class TestGetTrainingLog:
    def test_前回は開いた記録より前の同じ種目を含む最も新しい記録のトップセット(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        squat = _exercise(exercise_repo, "スクワット", e1rm_divisor=33.3)
        for on, weight in [(date(2026, 10, 2), 75.0), (date(2026, 10, 12), 80.0)]:
            _record(
                repo,
                exercise_repo,
                program_repo,
                on=on,
                sets_by_exercise=[(bench, [ExerciseSet(order=1, weight=weight, reps=5, rir=2)])],
            )
        previous_sets = [
            ExerciseSet(order=1, weight=72.5, reps=5, rir=3),
            ExerciseSet(order=2, weight=77.5, reps=5, rir=2),
        ]
        _record(repo, exercise_repo, program_repo, on=date(2026, 10, 6), sets_by_exercise=[(bench, previous_sets)])
        _record(repo, exercise_repo, program_repo, on=date(2026, 10, 8), sets_by_exercise=[(squat, previous_sets)])
        opened = _record(repo, exercise_repo, program_repo, on=date(2026, 10, 9), sets_by_exercise=[(bench, [])])

        detail = get_training_log(
            repo, exercise_repo=exercise_repo, program_repo=program_repo, uid=opened.training_log.uid
        )

        assert detail.exercises[0].previous == PreviousResult(
            date=date(2026, 10, 6), top_set=previous_sets[1], sets=tuple(previous_sets)
        )


class TestUpdatePerformedExercise:
    def test_差し替えると予定の回数と_RPE_のまま差し替え先の換算係数で目標重量を計算する(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        pause_bench = _exercise(exercise_repo, "ポーズベンチ", e1rm_divisor=None, parent=bench, coefficient=0.87)
        _set_training_max(exercise_repo, bench, 88.0)
        program = _program(program_repo, planned=(_planned(bench, order=1, target_rpe=7.0),))
        created = create_training_log(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            on=date(2026, 10, 12),
            program_day_uid=_day_uid(program, week=3, day=1),
            today=date(2026, 10, 12),
        )

        detail = update_performed_exercise(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            performed_uid=created.training_log.exercises[0].uid,
            exercise_uid=pause_bench.exercise.uid,
            memo="",
        )

        performed = detail.exercises[0]
        assert (
            performed.exercise.name,
            None if performed.planned is None else (performed.planned.reps, performed.planned.target_rpe),
            performed.target_weight,
        ) == ("ポーズベンチ", (5, 7.0), 65.0)


class TestListTrainingLogs:
    def test_前後の月の日を含む期間の記録が_Day_と種目ごとのトップセット付きで並ぶ(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        squat = _exercise(exercise_repo, "スクワット", e1rm_divisor=33.3)
        program = _program(program_repo, planned=())
        _record(
            repo,
            exercise_repo,
            program_repo,
            on=date(2026, 9, 28),
            sets_by_exercise=[(squat, [ExerciseSet(order=1, weight=100.0, reps=5, rir=2)])],
        )
        _record(
            repo,
            exercise_repo,
            program_repo,
            on=date(2026, 10, 9),
            program_day_uid=_day_uid(program, week=2, day=4),
            sets_by_exercise=[
                (
                    bench,
                    [
                        ExerciseSet(order=1, weight=75.0, reps=5, rir=2),
                        ExerciseSet(order=2, weight=77.5, reps=5, rir=2),
                    ],
                ),
                (squat, [ExerciseSet(order=1, weight=105.0, reps=5, rir=1)]),
            ],
        )
        _record(repo, exercise_repo, program_repo, on=date(2026, 11, 2), sets_by_exercise=[])

        summaries = list_training_logs(
            repo,
            exercise_repo=exercise_repo,
            program_repo=program_repo,
            from_date=date(2026, 9, 28),
            to_date=date(2026, 11, 1),
        )

        assert [
            (
                summary.training_log.date,
                None if summary.scheduled_day is None else summary.scheduled_day.day.day,
                [(top_set.exercise_name, top_set.exercise_set.weight) for top_set in summary.top_sets],
            )
            for summary in summaries
        ] == [
            (date(2026, 9, 28), None, [("スクワット", 100.0)]),
            (date(2026, 10, 9), 4, [("ベンチプレス", 77.5), ("スクワット", 105.0)]),
        ]


class TestListExerciseHistory:
    def test_派生種目でもその種目を含む記録が新しい順に並ぶ(
        self, repo: DbTrainingLogRepository, exercise_repo: DbExerciseRepository, program_repo: DbProgramRepository
    ) -> None:
        bench = _exercise(exercise_repo, "ベンチプレス")
        pause_bench = _exercise(exercise_repo, "ポーズベンチ", e1rm_divisor=None, parent=bench, coefficient=0.87)
        program = _program(program_repo, planned=())
        older_sets = [ExerciseSet(order=1, weight=65.0, reps=5, rir=2)]
        newer_sets = [
            ExerciseSet(order=1, weight=67.5, reps=5, rir=2),
            ExerciseSet(order=2, weight=67.5, reps=4, rir=1),
        ]
        _record(repo, exercise_repo, program_repo, on=date(2026, 10, 2), sets_by_exercise=[(pause_bench, older_sets)])
        _record(
            repo,
            exercise_repo,
            program_repo,
            on=date(2026, 10, 6),
            sets_by_exercise=[(bench, [ExerciseSet(order=1, weight=77.5, reps=5, rir=2)])],
        )
        _record(
            repo,
            exercise_repo,
            program_repo,
            on=date(2026, 10, 9),
            program_day_uid=_day_uid(program, week=2, day=4),
            sets_by_exercise=[(pause_bench, newer_sets)],
        )

        history = list_exercise_history(
            repo, exercise_repo=exercise_repo, program_repo=program_repo, exercise_uid=pause_bench.exercise.uid
        )

        assert [
            (
                record.entry.date,
                None if record.scheduled_day is None else record.scheduled_day.day.day,
                record.entry.sets,
            )
            for record in history
        ] == [(date(2026, 10, 9), 4, tuple(newer_sets)), (date(2026, 10, 2), None, tuple(older_sets))]


class _EvaluationRacingExerciseRepository(DbExerciseRepository):
    """評価済みかの確認と評価の書き込みの間に、並行した作成が同じ週を評価した状態を作る。"""

    def is_week_evaluated(self, week_start: date) -> bool:
        return False
