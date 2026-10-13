from datetime import UTC, datetime, timedelta

from features.rest_timer.types import PushMessage

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MICROSECOND = timedelta(microseconds=1)


def build_rest_finished_message(next_set_label: str) -> PushMessage:
    return PushMessage(title="レスト終了", body=next_set_label)


def to_epoch_microseconds(at: datetime) -> int:
    return (at - _EPOCH) // _MICROSECOND


def from_epoch_microseconds(epoch_microseconds: int) -> datetime:
    return _EPOCH + epoch_microseconds * _MICROSECOND
