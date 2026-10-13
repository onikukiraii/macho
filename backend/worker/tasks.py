from common.db.session import SessionLocal
from dependencies import get_invoice_repository, get_pdf_renderer, get_storage
from features.invoice import service
from worker.app import celery_app


@celery_app.task(name=service.ISSUE_TASK_NAME)
def issue_invoice_task(invoice_id: int) -> None:
    with SessionLocal() as session:
        service.issue_invoice(
            get_invoice_repository(session),
            get_storage(),
            get_pdf_renderer(),
            invoice_id=invoice_id,
        )
