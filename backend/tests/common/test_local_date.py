from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from common.local_date import to_local_date


class TestToLocalDate:
    def test_UTC_の_23_時は日本時間では翌日の日付になる(self) -> None:
        today = to_local_date(datetime(2026, 10, 13, 23, 0, tzinfo=UTC), timezone=ZoneInfo("Asia/Tokyo"))

        assert today == date(2026, 10, 14)
