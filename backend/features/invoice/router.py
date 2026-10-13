from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from common.errors import BusinessRuleViolation, NotFound, RenderError, StorageError
from common.gateway.protocol import JobQueue, Storage
from dependencies import get_invoice_repository, get_job_queue, get_pdf_renderer, get_storage
from features.invoice import service
from features.invoice.dto import (
    EnqueuedResponse,
    InvoiceCreateParams,
    InvoiceLineResponse,
    InvoiceResponse,
    PdfUrlResponse,
)
from features.invoice.protocol import InvoiceRepository, PdfRenderer
from features.invoice.types import Invoice, InvoiceLine

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/")
def get_invoices(repo: Annotated[InvoiceRepository, Depends(get_invoice_repository)]) -> list[InvoiceResponse]:
    return [_to_response(invoice) for invoice in service.list_invoices(repo)]


@router.post("/")
def create_invoice(
    params: InvoiceCreateParams,
    repo: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
) -> InvoiceResponse:
    invoice = service.create_invoice(
        repo,
        customer_name=params.customer_name,
        discount_rate=params.discount_rate,
        lines=[
            InvoiceLine(description=line.description, unit_price=line.unit_price, quantity=line.quantity)
            for line in params.lines
        ],
    )
    return _to_response(invoice)


@router.post("/{invoice_id}/issue")
def issue_invoice(
    invoice_id: int,
    repo: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
    storage: Annotated[Storage, Depends(get_storage)],
    renderer: Annotated[PdfRenderer, Depends(get_pdf_renderer)],
) -> InvoiceResponse:
    try:
        invoice = service.issue_invoice(repo, storage, renderer, invoice_id=invoice_id)
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    except (StorageError, RenderError) as e:
        raise HTTPException(502, "請求書 PDF の保存に失敗しました。") from e
    return _to_response(invoice)


@router.post("/{invoice_id}/issue-async")
def enqueue_issue(
    invoice_id: int,
    repo: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
    queue: Annotated[JobQueue, Depends(get_job_queue)],
) -> EnqueuedResponse:
    try:
        job_id = service.enqueue_issue(repo, queue, invoice_id=invoice_id)
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    return EnqueuedResponse(job_id=job_id)


@router.get("/{invoice_id}/pdf-url")
def get_pdf_url(
    invoice_id: int,
    repo: Annotated[InvoiceRepository, Depends(get_invoice_repository)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> PdfUrlResponse:
    try:
        url = service.invoice_pdf_url(repo, storage, invoice_id=invoice_id)
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except BusinessRuleViolation as e:
        raise HTTPException(400, str(e)) from e
    except StorageError as e:
        raise HTTPException(502, "請求書 PDF の URL 発行に失敗しました。") from e
    return PdfUrlResponse(url=url)


def _to_response(invoice: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=invoice.id,
        customer_name=invoice.customer_name,
        status=invoice.status,
        discount_rate=invoice.discount_rate,
        total=invoice.total,
        issued_at=invoice.issued_at,
        lines=[
            InvoiceLineResponse(description=line.description, unit_price=line.unit_price, quantity=line.quantity)
            for line in invoice.lines
        ],
    )
