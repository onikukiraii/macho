from datetime import date

from sqlalchemy.orm import Session

from features.program.repository import DbProgramRepository
from features.program.service import create_program
from features.program.types import NewProgram, NewProgramDay, NewProgramWeek, Weekday


class TestCreateProgram:
    def test_週と_Day_の昇順に_uid_を割り当てて作成する(self, db_session: Session) -> None:
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
        assert [(week.week, day.day) for week in created.weeks for day in week.days] == [(1, 1), (1, 2), (2, 1)]
        assert len(set(uids)) == 3
