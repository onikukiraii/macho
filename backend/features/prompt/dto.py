from pydantic import BaseModel


class PromptResponse(BaseModel):
    text: str
