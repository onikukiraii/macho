import pytest

from common.errors import BusinessRuleViolation, NotFound
from features.invoice._pure import invoice_object_key
from features.invoice.service import ISSUE_TASK_NAME, create_invoice, enqueue_issue, invoice_pdf_url, issue_invoice
from features.invoice.types import Invoice, InvoiceLine, InvoiceStatus
from tests.fakes import FakeJobQueue, FakePdfRenderer, FakeStorage, InMemoryInvoiceRepository


def _draft(invoice_id: int = 1, unit_price: int = 100_000) -> Invoice:
    return Invoice(
        id=invoice_id,
        customer_name="株式会社テスト",
        status=InvoiceStatus.draft,
        discount_rate=0.1,
        lines=[InvoiceLine(description="作業費", unit_price=unit_price, quantity=1)],
        total=None,
        issued_at=None,
    )


class TestIssueInvoice:
    def test_発行すると合計と発行日時が入る(self) -> None:
        repo = InMemoryInvoiceRepository([_draft()])

        issued = issue_invoice(repo, FakeStorage(), FakePdfRenderer(), invoice_id=1)

        assert issued.status is InvoiceStatus.issued
        assert issued.total == 99_000
        assert issued.issued_at is not None

    def test_pdf_を_storage_に置く(self) -> None:
        repo = InMemoryInvoiceRepository([_draft()])
        storage = FakeStorage()

        issue_invoice(repo, storage, FakePdfRenderer(), invoice_id=1)

        assert storage.objects[invoice_object_key(1)] == b"%PDF-fake"

    def test_発行済みは再発行できない(self) -> None:
        repo = InMemoryInvoiceRepository([_draft()])
        issue_invoice(repo, FakeStorage(), FakePdfRenderer(), invoice_id=1)
        storage = FakeStorage()

        with pytest.raises(BusinessRuleViolation):
            issue_invoice(repo, storage, FakePdfRenderer(), invoice_id=1)

        assert storage.objects == {}

    def test_存在しない_id_は_NotFound(self) -> None:
        with pytest.raises(NotFound):
            issue_invoice(InMemoryInvoiceRepository(), FakeStorage(), FakePdfRenderer(), invoice_id=999)


class TestEnqueueIssue:
    def test_タスク名と_invoice_id_を積む(self) -> None:
        repo = InMemoryInvoiceRepository([_draft()])
        queue = FakeJobQueue()

        job_id = enqueue_issue(repo, queue, invoice_id=1)

        assert queue.enqueued == [(ISSUE_TASK_NAME, {"invoice_id": 1})]
        assert job_id != ""

    def test_発行できない請求書は積まない(self) -> None:
        repo = InMemoryInvoiceRepository([_draft(unit_price=0)])
        queue = FakeJobQueue()

        with pytest.raises(BusinessRuleViolation):
            enqueue_issue(repo, queue, invoice_id=1)

        assert queue.enqueued == []


class TestInvoicePdfUrl:
    def test_発行済みなら_url_を返す(self) -> None:
        repo = InMemoryInvoiceRepository([_draft()])
        storage = FakeStorage()
        issue_invoice(repo, storage, FakePdfRenderer(), invoice_id=1)

        assert invoice_pdf_url(repo, storage, invoice_id=1) == "https://example.test/invoices/1.pdf"

    def test_下書きは_url_を返さない(self) -> None:
        repo = InMemoryInvoiceRepository([_draft()])

        with pytest.raises(BusinessRuleViolation):
            invoice_pdf_url(repo, FakeStorage(), invoice_id=1)


class TestCreateInvoice:
    def test_下書きとして作る(self) -> None:
        repo = InMemoryInvoiceRepository()

        invoice = create_invoice(
            repo,
            customer_name="株式会社テスト",
            discount_rate=0.0,
            lines=[InvoiceLine(description="作業費", unit_price=1_000, quantity=1)],
        )

        assert invoice.status is InvoiceStatus.draft
        assert invoice.total is None
