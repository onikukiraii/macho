from datetime import datetime

from pydantic import BaseModel, Field

from features.invoice.types import InvoiceStatus


class InvoiceLineParams(BaseModel):
    description: str
    unit_price: int = Field(ge=0)
    quantity: int = Field(ge=1)


class InvoiceCreateParams(BaseModel):
    customer_name: str
    discount_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    lines: list[InvoiceLineParams] = Field(min_length=1)


class InvoiceLineResponse(BaseModel):
    description: str
    unit_price: int
    quantity: int


class InvoiceResponse(BaseModel):
    id: int
    customer_name: str
    status: InvoiceStatus
    discount_rate: float
    total: int | None
    issued_at: datetime | None
    lines: list[InvoiceLineResponse]


class EnqueuedResponse(BaseModel):
    job_id: str


class PdfUrlResponse(BaseModel):
    url: str
