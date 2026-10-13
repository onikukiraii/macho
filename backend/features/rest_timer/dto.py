from datetime import datetime

from pydantic import BaseModel, Field


class PushSubscriptionCreateParams(BaseModel):
    endpoint: str = Field(min_length=1, max_length=500)
    p256dh: str
    auth: str


class RestTimerStartParams(BaseModel):
    seconds: int = Field(ge=1, le=1800)
    next_set_label: str = Field(max_length=100)


class RestTimerExtendParams(BaseModel):
    seconds: int = Field(ge=1, le=600)


class RestTimerResponse(BaseModel):
    started_at: datetime
    ends_at: datetime
    total_seconds: int
    next_set_label: str
