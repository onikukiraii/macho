from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from common.errors import BusinessRuleViolation, Conflict
from dependencies import get_user_repository
from features.user import service
from features.user.dto import UserCreateParams, UserResponse
from features.user.protocol import UserRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/")
def get_users(repo: Annotated[UserRepository, Depends(get_user_repository)]) -> list[UserResponse]:
    users = service.list_users(repo)
    return [UserResponse(id=u.id, name=u.name, email=u.email, created_at=u.created_at) for u in users]


@router.post("/")
def create_user(
    params: UserCreateParams,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    try:
        user = service.create_user(repo, name=params.name, email=params.email)
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    except Conflict as e:
        raise HTTPException(409, str(e)) from e
    return UserResponse(id=user.id, name=user.name, email=user.email, created_at=user.created_at)
