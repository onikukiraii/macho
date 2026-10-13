from datetime import date, datetime, tzinfo


def to_local_date(now: datetime, *, timezone: tzinfo) -> date:
    return now.astimezone(timezone).date()
