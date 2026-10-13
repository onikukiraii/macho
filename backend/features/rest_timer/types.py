from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PushResult(StrEnum):
    delivered = "delivered"
    expired = "expired"
    failed = "failed"


@dataclass(frozen=True)
class PushSubscription:
    id: int
    endpoint: str
    p256dh: str
    auth: str


@dataclass(frozen=True)
class RestTimer:
    uid: str
    started_at: datetime
    ends_at: datetime
    total_seconds: int
    next_set_label: str
