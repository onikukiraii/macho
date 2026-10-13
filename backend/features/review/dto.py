from datetime import datetime

from pydantic import BaseModel, Field

from features.review.types import ReviewStatus, Severity


class ReviewCreateParams(BaseModel):
    contract_text: str = Field(min_length=1)
    rules: list[str] = Field(min_length=1)


class FindingResponse(BaseModel):
    severity: Severity
    comment: str
    quote: str


class ReviewResponse(BaseModel):
    uid: str
    status: ReviewStatus
    summary: str | None
    findings: list[FindingResponse]
    created_at: datetime
