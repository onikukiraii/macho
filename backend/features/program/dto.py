from datetime import date, datetime

from pydantic import BaseModel, Field

# utf8mb4 の4バイト文字だけでも MySQL の TEXT の 65,535 バイトに収まる文字数
PROGRAM_TEXT_MAX_LENGTH = 16000


class ProgramRulesSaveParams(BaseModel):
    body: str = Field(max_length=PROGRAM_TEXT_MAX_LENGTH)


class ProgramRulesResponse(BaseModel):
    body: str
    updated_at: datetime | None


class PastProgramResponse(BaseModel):
    uid: str
    name: str
    start_date: date
    end_date: date
    week_count: int
    design_note: str
