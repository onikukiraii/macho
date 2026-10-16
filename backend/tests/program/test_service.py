from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from features.program.repository import DbProgramRepository, DbProgramRulesRepository
from features.program.service import create_program, get_program_rules, save_program_rules
from features.program.types import NewProgram, NewProgramDay, NewProgramWeek, Weekday


class TestCreateProgram:
    def test_Day_の件数ぶん重複しない_uid_を割り当てて作成する(self, db_session: Session) -> None:
        repo = DbProgramRepository(db_session)
        program = NewProgram(
            name="増量期",
            start_date=date(2026, 9, 28),
            tm_auto_update=True,
            design_note="",
            weeks=(
                NewProgramWeek(
                    week=2,
                    label="B",
                    days=(NewProgramDay(day=1, weekday=Weekday.mon, planned_exercises=()),),
                ),
                NewProgramWeek(
                    week=1,
                    label="A",
                    days=(
                        NewProgramDay(day=2, weekday=Weekday.wed, planned_exercises=()),
                        NewProgramDay(day=1, weekday=Weekday.mon, planned_exercises=()),
                    ),
                ),
            ),
        )

        created = create_program(repo, program=program)

        uids = [day.uid for week in created.weeks for day in week.days]
        assert len(set(uids)) == 3


class TestSaveProgramRules:
    def test_保存すると次に読むときは新しい本文と保存した日時になる(self, db_session: Session) -> None:
        repo = DbProgramRulesRepository(db_session)
        save_program_rules(repo, body="## 目標\n古い")
        before = datetime.now(UTC)

        save_program_rules(repo, body="## 目標\nBIG3 合計 400kg")

        rules = get_program_rules(repo)
        assert rules.body == "## 目標\nBIG3 合計 400kg"
        assert rules.updated_at is not None
        assert before <= rules.updated_at <= datetime.now(UTC)
