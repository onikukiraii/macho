from fastapi.testclient import TestClient


class TestGetReviewPrompt:
    def test_開始日が終了日より後なら_400(self, client: TestClient) -> None:
        response = client.get("/api/prompts/review", params={"from_date": "2026-10-14", "to_date": "2026-10-01"})

        assert (response.status_code, response.json()) == (400, {"detail": "開始日は終了日以前の日付にしてください"})
