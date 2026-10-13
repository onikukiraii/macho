from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreateParams(BaseModel):
    name: str
    email: EmailStr


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime
