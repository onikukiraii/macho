import pytest
from pydantic import BaseModel

from common.errors import LLMError, NotFound
from features.review.service import get_review, request_review
from features.review.types import FindingOutput, ReviewOutput, ReviewStatus, Severity
from tests.fakes import FakeLLM, InMemoryReviewRepository

OUTPUT = ReviewOutput(
    summary="重大な指摘が1件あります。",
    findings=[FindingOutput(severity=Severity.high, comment="解除条項がありません", quote="第5条")],
)


class TestRequestReview:
    def test_成功すると指摘とサマリが入る(self) -> None:
        repo = InMemoryReviewRepository()

        review = request_review(repo, FakeLLM([OUTPUT]), contract_text="本文", rules=["解除条項の有無"])

        assert review.status is ReviewStatus.succeeded
        assert review.summary == "重大な指摘が1件あります。"
        assert [finding.comment for finding in review.findings] == ["解除条項がありません"]

    def test_trace_id_に_uid_を渡す(self) -> None:
        repo = InMemoryReviewRepository()
        llm = FakeLLM([OUTPUT])

        review = request_review(repo, llm, contract_text="本文", rules=["解除条項の有無"])

        assert llm.trace_ids == [review.uid]

    def test_組み立てたプロンプトを渡す(self) -> None:
        llm = FakeLLM([OUTPUT])

        request_review(InMemoryReviewRepository(), llm, contract_text="第1条", rules=["解除条項の有無"])

        assert "第1条" in llm.prompts[0]
        assert "- 解除条項の有無" in llm.prompts[0]

    def test_LLM_が落ちたら_failed_で残して例外を投げる(self) -> None:
        repo = InMemoryReviewRepository()

        with pytest.raises(LLMError):
            request_review(repo, _FailingLLM(), contract_text="本文", rules=["解除条項の有無"])

        assert [review.status for review in repo.list_all()] == [ReviewStatus.failed]


class TestGetReview:
    def test_存在しない_uid_は_NotFound(self) -> None:
        with pytest.raises(NotFound):
            get_review(InMemoryReviewRepository(), uid="unknown")


class _FailingLLM:
    def complete[T: BaseModel](self, *, system: str, prompt: str, output: type[T], trace_id: str) -> T:
        raise LLMError("rate limited", retryable=True)
