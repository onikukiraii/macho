from datetime import UTC, datetime

from common.errors import BusinessRuleViolation
from common.gateway.protocol import JobQueue, Storage
from features.invoice._pure import calculate_amount, invoice_object_key, validate_issuable
from features.invoice.protocol import InvoiceRepository, PdfRenderer
from features.invoice.types import Invoice, InvoiceLine, InvoiceStatus

ISSUE_TASK_NAME = "invoice.issue"


def list_invoices(repo: InvoiceRepository) -> list[Invoice]:
    return repo.list_all()


def get_invoice(repo: InvoiceRepository, *, invoice_id: int) -> Invoice:
    return repo.get(invoice_id)


def create_invoice(
    repo: InvoiceRepository,
    *,
    customer_name: str,
    discount_rate: float,
    lines: list[InvoiceLine],
) -> Invoice:
    return repo.create(customer_name=customer_name, discount_rate=discount_rate, lines=lines)


def issue_invoice(
    repo: InvoiceRepository,
    storage: Storage,
    renderer: PdfRenderer,
    *,
    invoice_id: int,
) -> Invoice:
    invoice = repo.get(invoice_id)
    amount = calculate_amount(invoice.lines, invoice.discount_rate)
    validate_issuable(invoice.status, amount)

    issued = repo.save_issued(invoice, amount.total, issued_at=datetime.now(UTC))
    storage.put(invoice_object_key(invoice.id), renderer.render(invoice, amount), "application/pdf")
    return issued


def enqueue_issue(repo: InvoiceRepository, queue: JobQueue, *, invoice_id: int) -> str:
    invoice = repo.get(invoice_id)
    validate_issuable(invoice.status, calculate_amount(invoice.lines, invoice.discount_rate))
    return queue.enqueue(ISSUE_TASK_NAME, invoice_id=invoice.id)


def invoice_pdf_url(repo: InvoiceRepository, storage: Storage, *, invoice_id: int) -> str:
    invoice = repo.get(invoice_id)
    if invoice.status is InvoiceStatus.draft:
        raise BusinessRuleViolation("未発行の請求書には PDF がありません。")
    return storage.presigned_url(invoice_object_key(invoice.id))
