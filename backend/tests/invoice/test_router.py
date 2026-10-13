from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from dependencies import get_job_queue, get_pdf_renderer, get_storage
from main import app
from tests.fakes import FakeJobQueue, FakePdfRenderer, FakeStorage

CREATE_BODY = {
    "customer_name": "株式会社テスト",
    "discount_rate": 0.1,
    "lines": [{"description": "作業費", "unit_price": 100_000, "quantity": 1}],
}


@pytest.fixture()
def storage() -> Generator[FakeStorage]:
    fake = FakeStorage()
    app.dependency_overrides[get_storage] = lambda: fake
    app.dependency_overrides[get_pdf_renderer] = FakePdfRenderer
    yield fake
    app.dependency_overrides.pop(get_storage)
    app.dependency_overrides.pop(get_pdf_renderer)


@pytest.fixture()
def job_queue() -> Generator[FakeJobQueue]:
    fake = FakeJobQueue()
    app.dependency_overrides[get_job_queue] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_job_queue)


class TestCreateInvoice:
    def test_作成できる(self, client: TestClient) -> None:
        resp = client.post("/invoices/", json=CREATE_BODY)

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "draft"
        assert body["total"] is None
        assert len(body["lines"]) == 1

    def test_明細が空なら_422(self, client: TestClient) -> None:
        resp = client.post("/invoices/", json={**CREATE_BODY, "lines": []})

        assert resp.status_code == 422

    def test_割引率が1を超えたら_422(self, client: TestClient) -> None:
        resp = client.post("/invoices/", json={**CREATE_BODY, "discount_rate": 1.5})

        assert resp.status_code == 422


class TestIssueInvoice:
    def test_発行すると合計が入る(self, client: TestClient, storage: FakeStorage) -> None:
        invoice_id = client.post("/invoices/", json=CREATE_BODY).json()["id"]

        resp = client.post(f"/invoices/{invoice_id}/issue")

        assert resp.status_code == 200
        assert resp.json()["status"] == "issued"
        assert resp.json()["total"] == 99_000
        assert storage.objects[f"invoices/{invoice_id}.pdf"] == b"%PDF-fake"

    def test_存在しない_id_は_404(self, client: TestClient, storage: FakeStorage) -> None:
        assert client.post("/invoices/999/issue").status_code == 404

    def test_発行済みの再発行は_400(self, client: TestClient, storage: FakeStorage) -> None:
        invoice_id = client.post("/invoices/", json=CREATE_BODY).json()["id"]
        client.post(f"/invoices/{invoice_id}/issue")

        assert client.post(f"/invoices/{invoice_id}/issue").status_code == 400


class TestEnqueueIssue:
    def test_ジョブを積んで_job_id_を返す(self, client: TestClient, job_queue: FakeJobQueue) -> None:
        invoice_id = client.post("/invoices/", json=CREATE_BODY).json()["id"]

        resp = client.post(f"/invoices/{invoice_id}/issue-async")

        assert resp.status_code == 200
        assert resp.json()["job_id"] == "job-1"
        assert job_queue.enqueued == [("invoice.issue", {"invoice_id": invoice_id})]


class TestGetPdfUrl:
    def test_発行済みなら_url_を返す(self, client: TestClient, storage: FakeStorage) -> None:
        invoice_id = client.post("/invoices/", json=CREATE_BODY).json()["id"]
        client.post(f"/invoices/{invoice_id}/issue")

        resp = client.get(f"/invoices/{invoice_id}/pdf-url")

        assert resp.status_code == 200
        assert resp.json()["url"] == f"https://example.test/invoices/{invoice_id}.pdf"

    def test_下書きは_400(self, client: TestClient, storage: FakeStorage) -> None:
        invoice_id = client.post("/invoices/", json=CREATE_BODY).json()["id"]

        assert client.get(f"/invoices/{invoice_id}/pdf-url").status_code == 400
