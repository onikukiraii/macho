from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from common.errors import LLMError, NotFound
from common.gateway.protocol import LLM
from dependencies import get_llm, get_review_repository
from features.review import service
from features.review.dto import FindingResponse, ReviewCreateParams, ReviewResponse
from features.review.protocol import ReviewRepository
from features.review.types import Review

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/")
def get_reviews(repo: Annotated[ReviewRepository, Depends(get_review_repository)]) -> list[ReviewResponse]:
    return [_to_response(review) for review in service.list_reviews(repo)]


@router.get("/{uid}")
def get_review(uid: str, repo: Annotated[ReviewRepository, Depends(get_review_repository)]) -> ReviewResponse:
    try:
        review = service.get_review(repo, uid=uid)
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    return _to_response(review)


@router.post("/")
def request_review(
    params: ReviewCreateParams,
    repo: Annotated[ReviewRepository, Depends(get_review_repository)],
    llm: Annotated[LLM, Depends(get_llm)],
) -> ReviewResponse:
    try:
        review = service.request_review(repo, llm, contract_text=params.contract_text, rules=params.rules)
    except LLMError as e:
        status_code = 503 if e.retryable else 502
        raise HTTPException(status_code, "レビューの実行に失敗しました。") from e
    return _to_response(review)


def _to_response(review: Review) -> ReviewResponse:
    return ReviewResponse(
        uid=review.uid,
        status=review.status,
        summary=review.summary,
        findings=[FindingResponse(severity=f.severity, comment=f.comment, quote=f.quote) for f in review.findings],
        created_at=review.created_at,
    )
