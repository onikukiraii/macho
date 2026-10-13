from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from common.db.entities import ReviewFindingRow, ReviewRow
from common.errors import NotFound
from features.review.types import Review, ReviewFinding, ReviewStatus, Severity


class DbReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, uid: str) -> Review:
        return _to_domain(self._get_row(uid))

    def list_all(self) -> list[Review]:
        statement = select(ReviewRow).options(selectinload(ReviewRow.findings)).order_by(ReviewRow.id)
        return [_to_domain(row) for row in self._session.execute(statement).scalars().all()]

    def create_running(self, *, uid: str, contract_text: str) -> Review:
        row = ReviewRow(uid=uid, contract_text=contract_text, status=ReviewStatus.running)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)

    def save_succeeded(self, uid: str, *, summary: str, findings: list[ReviewFinding]) -> Review:
        row = self._get_row(uid)
        row.status = ReviewStatus.succeeded
        row.summary = summary
        row.findings = [
            ReviewFindingRow(severity=finding.severity, comment=finding.comment, quote=finding.quote)
            for finding in findings
        ]
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)

    def save_failed(self, uid: str) -> Review:
        row = self._get_row(uid)
        row.status = ReviewStatus.failed
        self._session.commit()
        self._session.refresh(row)
        return _to_domain(row)

    def _get_row(self, uid: str) -> ReviewRow:
        statement = select(ReviewRow).options(selectinload(ReviewRow.findings)).where(ReviewRow.uid == uid)
        row = self._session.execute(statement).scalar_one_or_none()
        if row is None:
            raise NotFound(f"review が見つかりません: uid={uid}")
        return row


def _to_domain(row: ReviewRow) -> Review:
    return Review(
        uid=row.uid,
        status=ReviewStatus(row.status),
        contract_text=row.contract_text,
        summary=row.summary,
        findings=[ReviewFinding(severity=Severity(f.severity), comment=f.comment, quote=f.quote) for f in row.findings],
        created_at=row.created_at,
    )
