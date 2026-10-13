from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ReviewStatus(StrEnum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class Severity(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class FindingOutput(BaseModel):
    severity: Severity
    comment: str
    quote: str


class ReviewOutput(BaseModel):
    summary: str
    findings: list[FindingOutput]


@dataclass(frozen=True)
class ReviewFinding:
    severity: Severity
    comment: str
    quote: str


@dataclass(frozen=True)
class Review:
    uid: str
    status: ReviewStatus
    contract_text: str
    summary: str | None
    findings: list[ReviewFinding]
    created_at: datetime
