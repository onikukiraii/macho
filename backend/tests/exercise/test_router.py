from typing import Any

import pytest
from fastapi.testclient import TestClient

from features.exercise.types import BodyPart, ExerciseKind, TrainingMaxSource

BENCH = {
    "name": "ベンチプレス",
    "body_part": BodyPart.chest,
    "parent_uid": None,
    "coefficient": None,
    "e1rm_divisor": 40.0,
    "increment_kg": 2.5,
    "default_rest_seconds": 180,
}
SQUAT = {
    "name": "スクワット",
    "body_part": BodyPart.legs,
    "parent_uid": None,
    "coefficient": None,
    "e1rm_divisor": 33.3,
    "increment_kg": 2.5,
    "default_rest_seconds": 180,
}


class TestCreateExercise:
    def test_保存した種目が一覧と詳細に表示される(self, client: TestClient) -> None:
        bench_uid = client.post("/api/exercises", json=BENCH).json()["uid"]
        client.post(f"/api/exercises/{bench_uid}/training-maxes", json={"value": 100.0, "reason": "初期値"})

        resp = client.post(
            "/api/exercises",
            json={
                "name": "ポーズベンチ",
                "body_part": BodyPart.chest,
                "parent_uid": bench_uid,
                "coefficient": 0.87,
                "e1rm_divisor": None,
                "increment_kg": 1.25,
                "default_rest_seconds": 120,
            },
        )
        created = resp.json()
        all_listed = client.get("/api/exercises").json()
        listed = [exercise for exercise in all_listed if exercise["uid"] == created["uid"]]
        detail = client.get(f"/api/exercises/{created['uid']}").json()

        expected = {
            "uid": created["uid"],
            "name": "ポーズベンチ",
            "body_part": BodyPart.chest,
            "kind": ExerciseKind.derived,
            "parent_uid": bench_uid,
            "parent_name": "ベンチプレス",
            "coefficient": 0.87,
            "e1rm_divisor": 40.0,
            "increment_kg": 1.25,
            "default_rest_seconds": 120,
            "current_training_max": None,
        }
        assert resp.status_code == 200
        assert listed == [expected]
        assert detail["exercise"] == expected
        assert {exercise["uid"]: exercise["kind"] for exercise in all_listed}[bench_uid] == ExerciseKind.training_max

    @pytest.mark.parametrize(
        "e1rm_divisor",
        [pytest.param("Infinity", id="無限大"), pytest.param("100.5", id="100超え")],
    )
    def test_分母が無限大か_100_を超えると_422(self, client: TestClient, e1rm_divisor: str) -> None:
        body = (
            '{"name": "スクワット", "body_part": "legs", "parent_uid": null, "coefficient": null, '
            f'"e1rm_divisor": {e1rm_divisor}, "increment_kg": 2.5, "default_rest_seconds": 180}}'
        )

        resp = client.post("/api/exercises", content=body, headers={"Content-Type": "application/json"})

        assert resp.status_code == 422
        assert [error["loc"][-1] for error in resp.json()["detail"]] == ["e1rm_divisor"]

    def test_分母が_100_ちょうどなら保存できる(self, client: TestClient) -> None:
        resp = client.post("/api/exercises", json={**SQUAT, "e1rm_divisor": 100.0})

        assert resp.status_code == 200
        assert resp.json()["e1rm_divisor"] == 100.0

    @pytest.mark.parametrize(
        "name",
        [
            pytest.param("", id="空"),
            pytest.param("   ", id="空白のみ"),
            pytest.param("スク\x00ワット", id="NUL"),
            pytest.param("スク\tワット", id="タブ"),
            pytest.param("スク\x7fワット", id="DEL"),
            pytest.param("\u200b", id="ゼロ幅のみ"),
            pytest.param("スク\u200bワット", id="ゼロ幅混在"),
        ],
    )
    def test_種目名が空白のみか制御文字とゼロ幅文字を含むと_422(self, client: TestClient, name: str) -> None:
        resp = client.post("/api/exercises", json={**SQUAT, "name": name})

        assert resp.status_code == 422
        assert [error["loc"][-1] for error in resp.json()["detail"]] == ["name"]

    def test_種目名の前後の空白は除いて保存される(self, client: TestClient) -> None:
        resp = client.post("/api/exercises", json={**SQUAT, "name": "  スクワット  "})

        assert resp.json()["name"] == "スクワット"

    def test_前後の空白を除くと既存の種目と同じ名前なら_409(self, client: TestClient) -> None:
        client.post("/api/exercises", json=SQUAT)

        resp = client.post("/api/exercises", json={**SQUAT, "name": "スクワット "})

        assert resp.status_code == 409

    def test_部位が6つのどれでもなければ_422(self, client: TestClient) -> None:
        resp = client.post("/api/exercises", json={**SQUAT, "body_part": "neck"})

        assert resp.status_code == 422
        assert [error["loc"][-1] for error in resp.json()["detail"]] == ["body_part"]


class TestUpdateExercise:
    def test_部位を変更すると詳細の部位が変わる(self, client: TestClient) -> None:
        uid = client.post("/api/exercises", json=SQUAT).json()["uid"]

        resp = client.put(f"/api/exercises/{uid}", json={**SQUAT, "body_part": BodyPart.back})

        assert resp.status_code == 200
        assert client.get(f"/api/exercises/{uid}").json()["exercise"]["body_part"] == BodyPart.back


class TestGetExercise:
    def test_存在しない_uid_なら_404(self, client: TestClient) -> None:
        resp = client.get("/api/exercises/no-such-uid")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "種目が見つかりません: uid=no-such-uid"


class TestCreateTrainingMax:
    def test_変更すると応答の現在値が新しい値になる(self, client: TestClient) -> None:
        squat_uid = client.post("/api/exercises", json=SQUAT).json()["uid"]
        client.post(f"/api/exercises/{squat_uid}/training-maxes", json={"value": 125.0, "reason": "初期値"})

        resp = client.post(
            f"/api/exercises/{squat_uid}/training-maxes",
            json={"value": 122.5, "reason": "腰の違和感で2週間落とす"},
        )

        detail = client.get(f"/api/exercises/{squat_uid}").json()
        assert resp.status_code == 200
        assert resp.json()["exercise"]["current_training_max"] == 122.5
        assert detail["exercise"]["current_training_max"] == 122.5
        assert [(entry["value"], entry["source"]) for entry in detail["training_max_history"]][:1] == [
            (122.5, TrainingMaxSource.manual)
        ]

    def test_値が_0_01_のような小さい正の値でも登録できる(self, client: TestClient) -> None:
        squat_uid = client.post("/api/exercises", json=SQUAT).json()["uid"]

        resp = client.post(f"/api/exercises/{squat_uid}/training-maxes", json={"value": 0.01, "reason": "入力"})

        assert resp.status_code == 200
        assert resp.json()["exercise"]["current_training_max"] == 0.01

    @pytest.mark.parametrize(
        "reason",
        [
            pytest.param("   ", id="空白のみ"),
            pytest.param("腰\x00痛", id="NUL"),
            pytest.param("腰\x7f痛", id="DEL"),
            pytest.param("\u200b", id="ゼロ幅のみ"),
            pytest.param("腰\u200b痛", id="ゼロ幅混在"),
        ],
    )
    def test_理由が空白のみか制御文字とゼロ幅文字を含むと_422(self, client: TestClient, reason: str) -> None:
        squat_uid = client.post("/api/exercises", json=SQUAT).json()["uid"]

        resp = client.post(f"/api/exercises/{squat_uid}/training-maxes", json={"value": 100.0, "reason": reason})

        assert resp.status_code == 422
        assert [error["loc"][-1] for error in resp.json()["detail"]] == ["reason"]

    def test_存在しない_uid_なら_404(self, client: TestClient) -> None:
        resp = client.post("/api/exercises/no-such-uid/training-maxes", json={"value": 100.0, "reason": "入力"})

        assert resp.status_code == 404
        assert resp.json()["detail"] == "種目が見つかりません: uid=no-such-uid"

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
