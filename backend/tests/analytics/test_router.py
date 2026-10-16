import pytest
from fastapi.testclient import TestClient

from features.exercise.types import BodyPart

BENCH = {
    "name": "ベンチプレス",
    "body_part": BodyPart.chest,
    "parent_uid": None,
    "coefficient": None,
    "e1rm_divisor": 40.0,
    "increment_kg": 2.5,
    "default_rest_seconds": 180,
}
REVERSED_PERIOD = {"from_date": "2026-10-14", "to_date": "2026-10-01"}


class TestAnalyticsPeriod:
    @pytest.mark.parametrize("target", ["overview", "exercise"])
    def test_開始日が終了日より後なら_400(self, client: TestClient, target: str) -> None:
        bench_uid = client.post("/api/exercises", json=BENCH).json()["uid"]
        path = "/api/analytics/overview" if target == "overview" else f"/api/analytics/exercises/{bench_uid}"

        response = client.get(path, params=REVERSED_PERIOD)

        assert (response.status_code, response.json()) == (400, {"detail": "開始日は終了日以前の日付にしてください"})


class TestGetExerciseAnalytics:
    def test_存在しない種目なら_404(self, client: TestClient) -> None:
        response = client.get(
            "/api/analytics/exercises/missing", params={"from_date": "2026-10-01", "to_date": "2026-10-14"}
        )

        assert response.status_code == 404
