from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from common.errors import JobQueueUnavailable, NotFound
from common.gateway.protocol import JobQueue
from dependencies import get_job_queue, get_rest_timer_repository
from features.rest_timer import service
from features.rest_timer.dto import (
    PushSubscriptionCreateParams,
    RestTimerExtendParams,
    RestTimerResponse,
    RestTimerStartParams,
)
from features.rest_timer.protocol import RestTimerRepository
from features.rest_timer.types import RestTimer

router = APIRouter(prefix="/api/rest-timer", tags=["rest-timer"])


@router.post("/push-subscriptions", status_code=204)
def create_push_subscription(
    params: PushSubscriptionCreateParams,
    repo: Annotated[RestTimerRepository, Depends(get_rest_timer_repository)],
) -> None:
    service.register_push_subscription(repo, endpoint=params.endpoint, p256dh=params.p256dh, auth=params.auth)


@router.get("")
def get_rest_timer(
    repo: Annotated[RestTimerRepository, Depends(get_rest_timer_repository)],
) -> RestTimerResponse | None:
    timer = service.get_rest_timer(repo)
    return _to_response(timer) if timer is not None else None


@router.post("")
def create_rest_timer(
    params: RestTimerStartParams,
    repo: Annotated[RestTimerRepository, Depends(get_rest_timer_repository)],
    job_queue: Annotated[JobQueue, Depends(get_job_queue)],
) -> RestTimerResponse:
    try:
        timer = service.start_rest_timer(repo, job_queue, seconds=params.seconds, next_set_label=params.next_set_label)
    except JobQueueUnavailable as e:
        raise HTTPException(503, "レストタイマーを開始できませんでした") from e
    return _to_response(timer)


@router.post("/extend")
def extend_rest_timer(
    params: RestTimerExtendParams,
    repo: Annotated[RestTimerRepository, Depends(get_rest_timer_repository)],
    job_queue: Annotated[JobQueue, Depends(get_job_queue)],
) -> RestTimerResponse:
    try:
        timer = service.extend_rest_timer(repo, job_queue, seconds=params.seconds)
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except JobQueueUnavailable as e:
        raise HTTPException(503, "レストタイマーを延長できませんでした") from e
    return _to_response(timer)


@router.delete("", status_code=204)
def delete_rest_timer(repo: Annotated[RestTimerRepository, Depends(get_rest_timer_repository)]) -> None:
    service.stop_rest_timer(repo)


def _to_response(timer: RestTimer) -> RestTimerResponse:
    return RestTimerResponse(
        started_at=timer.started_at,
        ends_at=timer.ends_at,
        total_seconds=timer.total_seconds,
        next_set_label=timer.next_set_label,
    )
