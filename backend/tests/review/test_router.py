from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from common.errors import LLMError
from dependencies import get_llm
from features.review.types import FindingOutput, ReviewOutput, Severity
from main import app
from tests.fakes import FakeLLM

CREATE_BODY = {"contract_text": "第1条 本契約は…", "rules": ["解除条項の有無"]}
OUTPUT = ReviewOutput(
    summary="重大な指摘が1件あります。",
    findings=[FindingOutput(severity=Severity.high, comment="解除条項がありません", quote="第5条")],
)


@pytest.fixture()
def llm() -> Generator[FakeLLM]:
    fake = FakeLLM([OUTPUT])
    app.dependency_overrides[get_llm] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_llm)


class TestRequestReview:
    def test_レビュー結果を返す(self, client: TestClient, llm: FakeLLM) -> None:
        resp = client.post("/reviews/", json=CREATE_BODY)

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "succeeded"
        assert body["findings"][0]["severity"] == "high"

    def test_観点が空なら_422(self, client: TestClient, llm: FakeLLM) -> None:
        assert client.post("/reviews/", json={**CREATE_BODY, "rules": []}).status_code == 422

    def test_LLM_がリトライ可能な失敗なら_503(self, client: TestClient) -> None:
        app.dependency_overrides[get_llm] = _RetryableLLM
        try:
            assert client.post("/reviews/", json=CREATE_BODY).status_code == 503
        finally:
            app.dependency_overrides.pop(get_llm)


class TestGetReview:
    def test_uid_で引ける(self, client: TestClient, llm: FakeLLM) -> None:
        uid = client.post("/reviews/", json=CREATE_BODY).json()["uid"]

        resp = client.get(f"/reviews/{uid}")

        assert resp.status_code == 200
        assert resp.json()["uid"] == uid

    def test_存在しない_uid_は_404(self, client: TestClient) -> None:
        assert client.get("/reviews/unknown").status_code == 404


class _RetryableLLM:
    def complete(self, *, system: str, prompt: str, output: type, trace_id: str) -> None:
        raise LLMError("rate limited", retryable=True)
