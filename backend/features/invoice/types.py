from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class InvoiceStatus(StrEnum):
    draft = "draft"
    issued = "issued"
    paid = "paid"


@dataclass(frozen=True)
class InvoiceLine:
    description: str
    unit_price: int
    quantity: int


@dataclass(frozen=True)
class InvoiceAmount:
    subtotal: int
    discount: int
    tax: int
    total: int


@dataclass(frozen=True)
class Invoice:
    id: int
    customer_name: str
    status: InvoiceStatus
    discount_rate: float
    lines: list[InvoiceLine]
    total: int | None
    issued_at: datetime | None
