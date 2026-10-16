import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from common.errors import BusinessRuleViolation
from dependencies import (
    get_exercise_repository,
    get_program_repository,
    get_program_rules_repository,
    get_today,
    get_training_log_repository,
)
from features.exercise.protocol import ExerciseRepository
from features.program.protocol import ProgramRepository, ProgramRulesRepository
from features.prompt import service
from features.prompt.dto import PromptResponse
from features.training_log.protocol import TrainingLogRepository

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

ProgramRepositoryDep = Annotated[ProgramRepository, Depends(get_program_repository)]
ProgramRulesRepositoryDep = Annotated[ProgramRulesRepository, Depends(get_program_rules_repository)]
ExerciseRepositoryDep = Annotated[ExerciseRepository, Depends(get_exercise_repository)]
TrainingLogRepositoryDep = Annotated[TrainingLogRepository, Depends(get_training_log_repository)]


@router.get("/program-generation")
def get_program_generation_prompt(
    program_repo: ProgramRepositoryDep,
    rules_repo: ProgramRulesRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    training_log_repo: TrainingLogRepositoryDep,
    today: Annotated[dt.date, Depends(get_today)],
) -> PromptResponse:
    text = service.get_generation_prompt(
        program_repo=program_repo,
        rules_repo=rules_repo,
        exercise_repo=exercise_repo,
        training_log_repo=training_log_repo,
        today=today,
    )
    return PromptResponse(text=text)


@router.get("/review")
def get_review_prompt(
    from_date: dt.date,
    to_date: dt.date,
    program_repo: ProgramRepositoryDep,
    rules_repo: ProgramRulesRepositoryDep,
    exercise_repo: ExerciseRepositoryDep,
    training_log_repo: TrainingLogRepositoryDep,
) -> PromptResponse:
    try:
        text = service.get_review_prompt(
            program_repo=program_repo,
            rules_repo=rules_repo,
            exercise_repo=exercise_repo,
            training_log_repo=training_log_repo,
            from_date=from_date,
            to_date=to_date,
        )
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    return PromptResponse(text=text)
