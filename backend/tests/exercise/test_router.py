from typing import Any

import pytest
from fastapi.testclient import TestClient

from features.exercise.types import ExerciseKind

BENCH = {
    "name": "ベンチプレス",
    "parent_uid": None,
    "coefficient": None,
    "e1rm_divisor": 40.0,
    "increment_kg": 2.5,
    "default_rest_seconds": 180,
}
SQUAT = {
    "name": "スクワット",
    "parent_uid": None,
    "coefficient": None,
    "e1rm_divisor": 33.3,
    "increment_kg": 2.5,
    "default_rest_seconds": 180,
}


class TestCreateExercise:
    def test_保存した種目が一覧と詳細に表示される(self, client: TestClient) -> None:
        bench_uid = client.post("/api/exercises", json=BENCH).json()["uid"]

        created = client.post(
            "/api/exercises",
            json={
                "name": "ポーズベンチ",
                "parent_uid": bench_uid,
                "coefficient": 0.87,
                "e1rm_divisor": None,
                "increment_kg": 2.5,
                "default_rest_seconds": 120,
            },
        ).json()
        listed = [exercise for exercise in client.get("/api/exercises").json() if exercise["uid"] == created["uid"]]
        detail = client.get(f"/api/exercises/{created['uid']}").json()

        expected = {
            "uid": created["uid"],
            "name": "ポーズベンチ",
            "kind": ExerciseKind.derived,
            "parent_uid": bench_uid,
            "parent_name": "ベンチプレス",
            "coefficient": 0.87,
            "e1rm_divisor": 40.0,
            "increment_kg": 2.5,
            "default_rest_seconds": 120,
            "current_training_max": None,
        }
        assert listed == [expected]
        assert detail["exercise"] == expected

    @pytest.mark.parametrize(
        "e1rm_divisor",
        [pytest.param("Infinity", id="無限大"), pytest.param("100.5", id="100超え")],
    )
    def test_分母が無限大か_100_を超えると_422(self, client: TestClient, e1rm_divisor: str) -> None:
        body = (
            '{"name": "スクワット", "parent_uid": null, "coefficient": null, '
            f'"e1rm_divisor": {e1rm_divisor}, "increment_kg": 2.5, "default_rest_seconds": 180}}'
        )

        resp = client.post("/api/exercises", content=body, headers={"Content-Type": "application/json"})

        assert resp.status_code == 422
        assert [error["loc"][-1] for error in resp.json()["detail"]] == ["e1rm_divisor"]


class TestCreateTrainingMax:
    def test_変更すると応答の現在値が新しい値になる(self, client: TestClient) -> None:
        squat_uid = client.post("/api/exercises", json=SQUAT).json()["uid"]
        client.post(f"/api/exercises/{squat_uid}/training-maxes", json={"value": 125.0, "reason": "初期値"})

        resp = client.post(
            f"/api/exercises/{squat_uid}/training-maxes",
            json={"value": 122.5, "reason": "腰の違和感で2週間落とす"},
        )

        assert resp.status_code == 200
        assert resp.json()["exercise"]["current_training_max"] == 122.5

    @pytest.mark.parametrize(
        ("params", "field"),
        [
            pytest.param({"value": 0, "reason": "入力"}, "value", id="値が0"),
            pytest.param({"value": -2.5, "reason": "入力"}, "value", id="値が負"),
            pytest.param({"value": 100.0, "reason": ""}, "reason", id="理由が空"),
        ],
    )
    def test_TM_の値が0以下か理由が空なら_422(self, client: TestClient, params: dict[str, Any], field: str) -> None:
        squat_uid = client.post("/api/exercises", json=SQUAT).json()["uid"]

        resp = client.post(f"/api/exercises/{squat_uid}/training-maxes", json=params)

        assert resp.status_code == 422
        assert [error["loc"][-1] for error in resp.json()["detail"]] == [field]
