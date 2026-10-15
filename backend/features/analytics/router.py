import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from common.errors import BusinessRuleViolation, NotFound
from dependencies import get_exercise_repository, get_today, get_training_log_repository
from features.analytics import service
from features.analytics.dto import (
    AnnualVolumeResponse,
    Big3LiftResponse,
    Big3TotalResponse,
    BodyPartShareResponse,
    BodyPartVolumeResponse,
    E1rmPointResponse,
    ExerciseAnalyticsResponse,
    ExerciseVolumeBucketResponse,
    MonthlyCumulativeVolumeResponse,
    OverviewResponse,
    PeriodSummaryResponse,
    TrainingMaxPointResponse,
    VolumeBucketResponse,
)
from features.analytics.types import ExerciseAnalytics, Overview, VolumeBucket
from features.exercise.protocol import ExerciseRepository
from features.training_log.protocol import TrainingLogRepository

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

TrainingLogRepositoryDep = Annotated[TrainingLogRepository, Depends(get_training_log_repository)]
ExerciseRepositoryDep = Annotated[ExerciseRepository, Depends(get_exercise_repository)]


@router.get("/overview")
def get_overview(
    from_date: dt.date,
    to_date: dt.date,
    training_log_repo: TrainingLogRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    today: Annotated[dt.date, Depends(get_today)],
) -> OverviewResponse:
    try:
        overview = service.get_overview(
            training_log_repo=training_log_repo,
            exercise_repo=exercise_repo,
            from_date=from_date,
            to_date=to_date,
            today=today,
        )
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    return _to_overview_response(overview)


@router.get("/exercises/{uid}")
def get_exercise_analytics(
    uid: str,
    from_date: dt.date,
    to_date: dt.date,
    training_log_repo: TrainingLogRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
) -> ExerciseAnalyticsResponse:
    try:
        analytics = service.get_exercise_analytics(
            training_log_repo=training_log_repo,
            exercise_repo=exercise_repo,
            exercise_uid=uid,
            from_date=from_date,
            to_date=to_date,
        )
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    return _to_exercise_response(analytics)


def _to_bucket_response(bucket: VolumeBucket) -> VolumeBucketResponse:
    return VolumeBucketResponse(
        start=bucket.start,
        volumes=[BodyPartVolumeResponse(body_part=v.body_part, volume=v.volume) for v in bucket.volumes],
    )


def _to_overview_response(overview: Overview) -> OverviewResponse:
    summary = overview.summary
    annual = overview.annual
    return OverviewResponse(
        summary=PeriodSummaryResponse(
            total_volume=summary.total_volume,
            change_rate=summary.change_rate,
            training_days=summary.training_days,
            set_count=summary.set_count,
            volume_per_training_day=summary.volume_per_training_day,
        ),
        weekly_volumes=[_to_bucket_response(bucket) for bucket in overview.weekly_volumes],
        monthly_volumes=[_to_bucket_response(bucket) for bucket in overview.monthly_volumes],
        body_part_shares=[
            BodyPartShareResponse(body_part=share.body_part, volume=share.volume, share=share.share)
            for share in overview.body_part_shares
        ],
        annual=AnnualVolumeResponse(
            year=annual.year,
            this_year=[
                MonthlyCumulativeVolumeResponse(month=m.month, cumulative_volume=m.cumulative_volume)
                for m in annual.this_year
            ],
            last_year=[
                MonthlyCumulativeVolumeResponse(month=m.month, cumulative_volume=m.cumulative_volume)
                for m in annual.last_year
            ],
            change_rate=annual.change_rate,
            last_year_total_volume=annual.last_year_total_volume,
        ),
        big3=Big3TotalResponse(
            lifts=[Big3LiftResponse(exercise_name=lift.exercise_name, e1rm=lift.e1rm) for lift in overview.big3.lifts],
            total=overview.big3.total,
            goal=overview.big3.goal,
        ),
    )


def _to_exercise_response(analytics: ExerciseAnalytics) -> ExerciseAnalyticsResponse:
    return ExerciseAnalyticsResponse(
        exercise_name=analytics.exercise_name,
        max_weight=analytics.max_weight,
        max_e1rm=analytics.max_e1rm,
        total_volume=analytics.total_volume,
        e1rm_points=[E1rmPointResponse(date=p.date, e1rm=p.e1rm) for p in analytics.e1rm_points],
        training_max_points=[
            TrainingMaxPointResponse(effective_on=p.effective_on, value=p.value) for p in analytics.training_max_points
        ],
        weekly_volumes=[ExerciseVolumeBucketResponse(start=b.start, volume=b.volume) for b in analytics.weekly_volumes],
        monthly_volumes=[
            ExerciseVolumeBucketResponse(start=b.start, volume=b.volume) for b in analytics.monthly_volumes
        ],
    )
