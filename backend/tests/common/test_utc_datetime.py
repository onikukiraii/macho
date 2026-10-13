from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from common.db.entities import RestTimerRow

JST = timezone(timedelta(hours=9))


def _timer(ends_at: datetime) -> RestTimerRow:
    return RestTimerRow(
        uid="u1",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        ends_at=ends_at,
        total_seconds=90,
        next_set_label="ベンチプレス 2セット目",
    )


class TestUtcDateTime:
    def test_読み出した_datetime_は_UTC_の_aware_で返る(self, db_session: Session) -> None:
        db_session.add(_timer(datetime(2026, 1, 1, 9, 0, 1, 123456, tzinfo=JST)))
        db_session.commit()
        db_session.expunge_all()

        row = db_session.scalars(select(RestTimerRow)).one()

        assert row.ends_at == datetime(2026, 1, 1, 0, 0, 1, 123456, tzinfo=UTC)
        assert row.ends_at.tzinfo is not None

    def test_naive_な_datetime_は書き込めない(self, db_session: Session) -> None:
        db_session.add(_timer(datetime(2026, 1, 1, 0, 0, 1)))

        with pytest.raises(StatementError, match="naive"):
            db_session.flush()
