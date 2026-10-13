import pytest
from sqlalchemy.orm import Session

from common.errors import NotFound
from features.review.repository import DbReviewRepository
from features.review.types import ReviewFinding, ReviewStatus, Severity

UID = "11111111-1111-1111-1111-111111111111"


class TestCreateRunning:
    def test_running_で作る(self, db_session: Session) -> None:
        repo = DbReviewRepository(db_session)

        review = repo.create_running(uid=UID, contract_text="第1条")

        assert review.status is ReviewStatus.running
        assert review.summary is None
        assert review.findings == []


class TestSaveSucceeded:
    def test_指摘とサマリを書き込む(self, db_session: Session) -> None:
        repo = DbReviewRepository(db_session)
        repo.create_running(uid=UID, contract_text="第1条")

        repo.save_succeeded(
            UID,
            summary="重大な指摘が1件あります。",
            findings=[ReviewFinding(severity=Severity.high, comment="解除条項がありません", quote="第5条")],
        )

        review = repo.get(UID)
        assert review.status is ReviewStatus.succeeded
        assert review.summary == "重大な指摘が1件あります。"
        assert [finding.severity for finding in review.findings] == [Severity.high]

    def test_二度目の保存で指摘が重複しない(self, db_session: Session) -> None:
        repo = DbReviewRepository(db_session)
        repo.create_running(uid=UID, contract_text="第1条")
        findings = [ReviewFinding(severity=Severity.low, comment="表記ゆれ", quote="第7条")]

        repo.save_succeeded(UID, summary="1回目", findings=findings)
        repo.save_succeeded(UID, summary="2回目", findings=findings)

        assert len(repo.get(UID).findings) == 1


class TestSaveFailed:
    def test_failed_にする(self, db_session: Session) -> None:
        repo = DbReviewRepository(db_session)
        repo.create_running(uid=UID, contract_text="第1条")

        repo.save_failed(UID)

        assert repo.get(UID).status is ReviewStatus.failed


class TestGet:
    def test_存在しない_uid_は_NotFound(self, db_session: Session) -> None:
        with pytest.raises(NotFound):
            DbReviewRepository(db_session).get("unknown")
