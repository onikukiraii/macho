from collections.abc import Generator
from typing import Annotated

import anthropic
import boto3
from fastapi import Depends
from sqlalchemy.orm import Session

from common.config import settings
from common.db.session import SessionLocal
from common.gateway.job_queue_celery import CeleryJobQueue
from common.gateway.llm_claude import ClaudeLLM
from common.gateway.protocol import LLM, JobQueue, Storage
from common.gateway.storage_s3 import S3Storage
from features.invoice.gateway import ReportLabPdfRenderer
from features.invoice.protocol import InvoiceRepository, PdfRenderer
from features.invoice.repository import DbInvoiceRepository
from features.review.protocol import ReviewRepository
from features.review.repository import DbReviewRepository
from features.user.protocol import UserRepository
from features.user.repository import DbUserRepository
from worker.app import celery_app


def get_session() -> Generator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]


def get_storage() -> Storage:
    return S3Storage(
        bucket=settings.s3_bucket,
        client=boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
        ),
    )


def get_llm() -> LLM:
    return ClaudeLLM(
        client=anthropic.Anthropic(),
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
    )


def get_job_queue() -> JobQueue:
    return CeleryJobQueue(celery_app)


def get_pdf_renderer() -> PdfRenderer:
    return ReportLabPdfRenderer()


def get_user_repository(session: SessionDep) -> UserRepository:
    return DbUserRepository(session)


def get_invoice_repository(session: SessionDep) -> InvoiceRepository:
    return DbInvoiceRepository(session)


def get_review_repository(session: SessionDep) -> ReviewRepository:
    return DbReviewRepository(session)
