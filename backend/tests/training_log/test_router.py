import json
from collections.abc import Callable, Generator, Sequence
from datetime import date
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from common.errors import Conflict
from dependencies import SessionDep, get_today, get_training_log_repository
from features.training_log.repository import DbTrainingLogRepository
from features.training_log.types import ExerciseSet, TrainingLog
from main import app

TODAY = date(2026, 10, 14)
BENCH = {
    "name": "ベンチプレス",
    "parent_uid": None,
    "coefficient": None,
    "e1rm_divisor": 40.0,
    "increment_kg": 2.5,
    "default_rest_seconds": 180,
}


@pytest.fixture()
def today_client(client: TestClient) -> Generator[TestClient]:
    app.dependency_overrides[get_today] = lambda: TODAY
    yield client
    app.dependency_overrides.pop(get_today)


def _create_log_with_bench(client: TestClient) -> tuple[dict[str, Any], str]:
    bench_uid = client.post("/api/exercises", json=BENCH).json()["uid"]
    log_uid = client.post("/api/training-logs", json={"date": TODAY.isoformat(), "program_day_uid": None}).json()["uid"]
    detail = client.post(f"/api/training-logs/{log_uid}/exercises", json={"exercise_uid": bench_uid}).json()
    return detail, bench_uid


class TestUpdateTrainingLog:
    @pytest.mark.parametrize(
        ("save_memo", "read_memo"),
        [
            pytest.param(
                lambda client, log, bench_uid: client.patch(
                    f"/api/training-logs/{log['uid']}", json={"memo": "肩に違和感"}
                ),
                lambda detail: detail["memo"],
                id="トレーニング記録のメモ",
            ),
            pytest.param(
                lambda client, log, bench_uid: client.patch(
                    f"/api/training-logs/exercises/{log['exercises'][0]['uid']}", json={"memo": "肩に違和感"}
                ),
                lambda detail: detail["exercises"][0]["memo"],
                id="種目のメモ",
            ),
        ],
    )
    def test_保存したメモは記録を開き直しても表示される(
        self,
        today_client: TestClient,
        save_memo: Callable[[TestClient, dict[str, Any], str], httpx.Response],
        read_memo: Callable[[dict[str, Any]], str],
    ) -> None:
        log, bench_uid = _create_log_with_bench(today_client)

        save_memo(today_client, log, bench_uid)
        reopened = today_client.get(f"/api/training-logs/{log['uid']}")

        assert (reopened.status_code, read_memo(reopened.json())) == (200, "肩に違和感")


class TestUpdatePerformedExercise:
    def test_メモのある種目を差し替えてもその種目のメモは残る(self, today_client: TestClient) -> None:
        log, _ = _create_log_with_bench(today_client)
        performed_uid = log["exercises"][0]["uid"]
        squat_uid = today_client.post("/api/exercises", json={**BENCH, "name": "スクワット"}).json()["uid"]
        today_client.patch(f"/api/training-logs/exercises/{performed_uid}", json={"memo": "肩に違和感"})

        resp = today_client.patch(f"/api/training-logs/exercises/{performed_uid}", json={"exercise_uid": squat_uid})
        reopened = today_client.get(f"/api/training-logs/{log['uid']}").json()["exercises"][0]

        assert resp.status_code == 200
        assert (reopened["exercise_name"], reopened["memo"]) == ("スクワット", "肩に違和感")

    def test_メモの保存で種目は変わらない(self, today_client: TestClient) -> None:
        log, _ = _create_log_with_bench(today_client)
        performed_uid = log["exercises"][0]["uid"]

        resp = today_client.patch(f"/api/training-logs/exercises/{performed_uid}", json={"memo": "肩に違和感"})

        assert resp.status_code == 200
        assert today_client.get(f"/api/training-logs/{log['uid']}").json()["exercises"][0]["exercise_name"] == (
            "ベンチプレス"
        )

    def test_空のメモを保存するとメモが空になる(self, today_client: TestClient) -> None:
        log, _ = _create_log_with_bench(today_client)
        performed_uid = log["exercises"][0]["uid"]
        today_client.patch(f"/api/training-logs/exercises/{performed_uid}", json={"memo": "肩に違和感"})

        resp = today_client.patch(f"/api/training-logs/exercises/{performed_uid}", json={"memo": ""})

        assert (resp.status_code, resp.json()["exercises"][0]["memo"]) == (200, "")

    def test_存在しない種目のメモは保存できず_404_を返す(self, today_client: TestClient) -> None:
        resp = today_client.patch("/api/training-logs/exercises/missing", json={"memo": "肩に違和感"})

        assert (resp.status_code, resp.json()["detail"]) == (404, "種目が見つかりません")

    def test_存在しない種目への差し替えは_404_で種目もメモも変わらない(self, today_client: TestClient) -> None:
        log, _ = _create_log_with_bench(today_client)
        performed_uid = log["exercises"][0]["uid"]
        today_client.patch(f"/api/training-logs/exercises/{performed_uid}", json={"memo": "肩に違和感"})

        resp = today_client.patch(f"/api/training-logs/exercises/{performed_uid}", json={"exercise_uid": "missing"})
        reopened = today_client.get(f"/api/training-logs/{log['uid']}").json()["exercises"][0]

        assert resp.status_code == 404
        assert (reopened["exercise_name"], reopened["memo"]) == ("ベンチプレス", "肩に違和感")

    @pytest.mark.parametrize(
        "body",
        [
            pytest.param({"exercise_uid": "x", "memo": "メモ"}, id="種目とメモの両方"),
            pytest.param({}, id="どちらも無い"),
            pytest.param({"exercise_uid": None}, id="種目が_null"),
            pytest.param({"memo": None}, id="メモが_null"),
            pytest.param(None, id="本文が_null"),
            pytest.param({"exercise_uid": ""}, id="種目が空文字"),
        ],
    )
    def test_種目とメモのどちらか1つだけを送らない更新は_422_で受け付けない(
        self, today_client: TestClient, body: dict[str, Any] | None
    ) -> None:
        log, _ = _create_log_with_bench(today_client)

        resp = today_client.patch(
            f"/api/training-logs/exercises/{log['exercises'][0]['uid']}",
            content=json.dumps(body),
            headers={"Content-Type": "application/json"},
        )

        assert resp.status_code == 422


class TestUpdateSets:
    @pytest.mark.parametrize(
        ("sets", "error_types"),
        [
            pytest.param([{"order": 1, "weight": -2.5, "reps": 5, "rir": 2}], ["greater_than_equal"], id="重量が負"),
            pytest.param([{"order": 1, "weight": 75.0, "reps": -1, "rir": 2}], ["greater_than_equal"], id="回数が負"),
            pytest.param([{"order": 1, "weight": 75.0, "reps": 5, "rir": -1}], ["greater_than_equal"], id="RIR_が負"),
            pytest.param(
                [{"order": 1, "weight": 75.0, "reps": 5, "rir": 11}], ["less_than_equal"], id="RIR_が_10_超え"
            ),
            pytest.param(
                [{"order": 1, "weight": 75.0, "reps": 5, "rir": 2}, {"order": 1, "weight": 77.5, "reps": 5, "rir": 1}],
                ["value_error"],
                id="同じセット番号が2つ",
            ),
            pytest.param(
                [{"order": order % 50 + 1, "weight": 75.0, "reps": 5, "rir": 2} for order in range(51)],
                ["too_long"],
                id="51件",
            ),
            pytest.param(
                [{"order": 51, "weight": 75.0, "reps": 5, "rir": 2}], ["less_than_equal"], id="セット番号が_51"
            ),
        ],
    )
    def test_不正なセットは_422_で保存できない(
        self, today_client: TestClient, sets: list[dict[str, Any]], error_types: list[str]
    ) -> None:
        log, _ = _create_log_with_bench(today_client)

        resp = today_client.put(f"/api/training-logs/exercises/{log['exercises'][0]['uid']}/sets", json={"sets": sets})

        assert (resp.status_code, [error["type"] for error in resp.json()["detail"]]) == (422, error_types)

    @pytest.mark.parametrize(
        "sets",
        [
            pytest.param([{"order": 1, "weight": 75.0, "reps": 5, "rir": 10}], id="RIR_が_10"),
            pytest.param([{"order": 1, "weight": 0.0, "reps": 5, "rir": 2}], id="重量が_0"),
            pytest.param([{"order": 1, "weight": 75.0, "reps": 0, "rir": 2}], id="回数が_0"),
            pytest.param([{"order": order, "weight": 75.0, "reps": 5, "rir": 2} for order in range(1, 51)], id="50件"),
            pytest.param([{"order": 50, "weight": 75.0, "reps": 5, "rir": 2}], id="セット番号が_50"),
        ],
    )
    def test_境界の値のセットは保存できる(self, today_client: TestClient, sets: list[dict[str, Any]]) -> None:
        log, _ = _create_log_with_bench(today_client)

        resp = today_client.put(f"/api/training-logs/exercises/{log['exercises'][0]['uid']}/sets", json={"sets": sets})

        assert (resp.status_code, resp.json()["sets"]) == (200, sets)

    def test_セットの保存が一意制約と衝突すると_409_を返す(self, today_client: TestClient) -> None:
        log, _ = _create_log_with_bench(today_client)
        app.dependency_overrides[get_training_log_repository] = _ConflictingTrainingLogRepository
        try:
            resp = today_client.put(
                f"/api/training-logs/exercises/{log['exercises'][0]['uid']}/sets",
                json={"sets": [{"order": 1, "weight": 75.0, "reps": 5, "rir": 2}]},
            )
        finally:
            app.dependency_overrides.pop(get_training_log_repository)

        assert (resp.status_code, resp.json()["detail"]) == (409, "同じ番号のセットがあります")


class TestGetTrainingLogs:
    @pytest.mark.parametrize(
        ("path", "params", "status_code", "read_detail", "detail"),
        [
            pytest.param(
                "/api/training-logs",
                {"from_date": "2026-11-01", "to_date": "2026-09-28"},
                400,
                lambda body: body["detail"],
                "開始日は終了日以前の日付にしてください",
                id="カレンダーの逆順",
            ),
            pytest.param(
                "/api/training-logs",
                {"from_date": "2026/09/28", "to_date": "2026-11-01"},
                422,
                lambda body: [error["loc"] for error in body["detail"]],
                [["query", "from_date"]],
                id="カレンダーの形式",
            ),
            pytest.param(
                "/api/training-logs/export",
                {"from_date": "2026-10-14", "to_date": "2026-09-14"},
                400,
                lambda body: body["detail"],
                "開始日は終了日以前の日付にしてください",
                id="CSV_の逆順",
            ),
            pytest.param(
                "/api/training-logs/export",
                {"from_date": "2026-09-14", "to_date": "10月14日"},
                422,
                lambda body: [error["loc"] for error in body["detail"]],
                [["query", "to_date"]],
                id="CSV_の形式",
            ),
        ],
    )
    def test_開始日が終了日より後か日付の形式でなければ取得できない(
        self,
        client: TestClient,
        path: str,
        params: dict[str, str],
        status_code: int,
        read_detail: Callable[[Any], object],
        detail: object,
    ) -> None:
        resp = client.get(path, params=params)

        assert (resp.status_code, read_detail(resp.json())) == (status_code, detail)


class TestGetTrainingLog:
    def test_存在しない記録は_404_で見つかりませんを返す(self, client: TestClient) -> None:
        resp = client.get("/api/training-logs/00000000-0000-0000-0000-000000000000")

        assert (resp.status_code, resp.json()["detail"]) == (404, "トレーニング記録が見つかりません")


class _ConflictingTrainingLogRepository(DbTrainingLogRepository):
    """並行したセットの保存が先に同じ番号のセットを書き、一意制約に違反した状態を作る。"""

    def __init__(self, session: SessionDep) -> None:
        super().__init__(session)

    def replace_sets(self, performed_uid: str, *, sets: Sequence[ExerciseSet]) -> TrainingLog:
        raise Conflict(f"同じ番号のセットがあります: uid={performed_uid}")
