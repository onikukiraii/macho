from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from common.errors import NotFound
from features.invoice.repository import DbInvoiceRepository
from features.invoice.types import InvoiceLine, InvoiceStatus


def _create(repo: DbInvoiceRepository, customer_name: str = "株式会社テスト") -> int:
    invoice = repo.create(
        customer_name=customer_name,
        discount_rate=0.1,
        lines=[
            InvoiceLine(description="作業費", unit_price=50_000, quantity=2),
            InvoiceLine(description="交通費", unit_price=1_000, quantity=1),
        ],
    )
    return invoice.id


class TestCreate:
    def test_明細ごと保存して下書きで返す(self, db_session: Session) -> None:
        repo = DbInvoiceRepository(db_session)

        invoice_id = _create(repo)

        invoice = repo.get(invoice_id)
        assert invoice.status is InvoiceStatus.draft
        assert [line.description for line in invoice.lines] == ["作業費", "交通費"]


class TestGet:
    def test_存在しない_id_は_NotFound(self, db_session: Session) -> None:
        with pytest.raises(NotFound):
            DbInvoiceRepository(db_session).get(999)


class TestListAll:
    def test_id_昇順で返す(self, db_session: Session) -> None:
        repo = DbInvoiceRepository(db_session)
        _create(repo, customer_name="A社")
        _create(repo, customer_name="B社")

        assert [invoice.customer_name for invoice in repo.list_all()] == ["A社", "B社"]


class TestSaveIssued:
    def test_状態と合計と発行日時を書き込む(self, db_session: Session) -> None:
        repo = DbInvoiceRepository(db_session)
        invoice_id = _create(repo)
        issued_at = datetime(2026, 9, 12, tzinfo=UTC)

        repo.save_issued(repo.get(invoice_id), 99_000, issued_at=issued_at)

        invoice = repo.get(invoice_id)
        assert invoice.status is InvoiceStatus.issued
        assert invoice.total == 99_000
        assert invoice.issued_at is not None
