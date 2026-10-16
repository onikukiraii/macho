from typing import Annotated

from fastapi import APIRouter, Depends

from dependencies import get_program_repository, get_program_rules_repository
from features.program import service
from features.program.dto import PastProgramResponse, ProgramRulesResponse, ProgramRulesSaveParams
from features.program.protocol import ProgramRepository, ProgramRulesRepository
from features.program.types import PastProgram, ProgramRules

router = APIRouter(prefix="/api/programs", tags=["programs"])

ProgramRulesRepositoryDep = Annotated[ProgramRulesRepository, Depends(get_program_rules_repository)]


@router.get("/rules")
def get_program_rules(repo: ProgramRulesRepositoryDep) -> ProgramRulesResponse:
    return _to_rules_response(service.get_program_rules(repo))


@router.put("/rules")
def update_program_rules(params: ProgramRulesSaveParams, repo: ProgramRulesRepositoryDep) -> ProgramRulesResponse:
    return _to_rules_response(service.save_program_rules(repo, body=params.body))


@router.get("/past")
def get_past_programs(
    repo: Annotated[ProgramRepository, Depends(get_program_repository)],
) -> list[PastProgramResponse]:
    return [_to_past_response(past) for past in service.list_past_programs(repo)]


def _to_rules_response(rules: ProgramRules) -> ProgramRulesResponse:
    return ProgramRulesResponse(body=rules.body, updated_at=rules.updated_at)


def _to_past_response(past: PastProgram) -> PastProgramResponse:
    return PastProgramResponse(
        uid=past.program.uid,
        name=past.program.name,
        start_date=past.program.start_date,
        end_date=past.end_date,
        week_count=len(past.program.weeks),
        design_note=past.program.design_note,
    )
