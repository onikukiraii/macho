from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from common.db.entities import InvoiceLineRow, InvoiceRow
from common.errors import NotFound
from features.invoice.types import Invoice, InvoiceLine, InvoiceStatus


class DbInvoiceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, invoice_id: int) -> Invoice:
        row = self._session.get(InvoiceRow, invoice_id, options=[selectinload(InvoiceRow.lines)])
        if row is None:
            raise NotFound(f"invoice が見つかりません: invoice_id={invoice_id}")
        return _to_domain(row)

    def list_all(self) -> list[Invoice]:
        statement = select(InvoiceRow).options(selectinload(InvoiceRow.lines)).order_by(InvoiceRow.id)
        return [_to_domain(row) for row in self._session.execute(statement).scalars().all()]

    def create(self, *, customer_name: str, discount_rate: float, lines: list[InvoiceLine]) -> Invoice:
        row = InvoiceRow(
            customer_name=customer_name,
            status=InvoiceStatus.draft,
            discount_rate=discount_rate,
            lines=[
                InvoiceLineRow(description=line.description, unit_price=line.unit_price, quantity=line.quantity)
                for line in lines
            ],
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)

    def save_issued(self, invoice: Invoice, total: int, *, issued_at: datetime) -> Invoice:
        row = self._session.get(InvoiceRow, invoice.id, options=[selectinload(InvoiceRow.lines)])
        if row is None:
            raise NotFound(f"invoice が見つかりません: invoice_id={invoice.id}")
        row.status = InvoiceStatus.issued
        row.total = total
        row.issued_at = issued_at
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)


def _to_domain(row: InvoiceRow) -> Invoice:
    return Invoice(
        id=row.id,
        customer_name=row.customer_name,
        status=InvoiceStatus(row.status),
        discount_rate=row.discount_rate,
        lines=[
            InvoiceLine(description=line.description, unit_price=line.unit_price, quantity=line.quantity)
            for line in row.lines
        ],
        total=row.total,
        issued_at=row.issued_at,
    )
