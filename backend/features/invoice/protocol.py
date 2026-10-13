from datetime import datetime
from typing import Protocol

from features.invoice.types import Invoice, InvoiceAmount, InvoiceLine


class InvoiceRepository(Protocol):
    def get(self, invoice_id: int) -> Invoice: ...

    def list_all(self) -> list[Invoice]: ...

    def create(self, *, customer_name: str, discount_rate: float, lines: list[InvoiceLine]) -> Invoice: ...

    def save_issued(self, invoice: Invoice, total: int, *, issued_at: datetime) -> Invoice: ...


class PdfRenderer(Protocol):
    def render(self, invoice: Invoice, amount: InvoiceAmount) -> bytes: ...
