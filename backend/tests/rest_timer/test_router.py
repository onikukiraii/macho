import base64
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from common.errors import JobQueueUnavailable
from dependencies import get_job_queue
from features.rest_timer.repository import DbRestTimerRepository
from features.rest_timer.types import RestTimer
from main import app
from tests.fakes import FakeJobQueue


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


P256DH = _b64url(
    ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
)
AUTH = _b64url(b"\x02" * 16)
ENDPOINT = "https://web.push.apple.com/QGuQyavXutnMH"


@pytest.fixture()
def job_queue_client(client: TestClient) -> Generator[TestClient]:
    app.dependency_overrides[get_job_queue] = FakeJobQueue
    yield client
    app.dependency_overrides.pop(get_job_queue)


@pytest.fixture()
def failing_job_queue_client(client: TestClient) -> Generator[TestClient]:
    app.dependency_overrides[get_job_queue] = _FailingJobQueue
    yield client
    app.dependency_overrides.pop(get_job_queue)


def _save_running_timer(db_session: Session) -> RestTimer:
    now = datetime.now(UTC)
    timer = RestTimer(
        uid="0d6f2c1e-8a4b-4f3e-9c2d-1b5a7e9f0c3d",
        started_at=now - timedelta(seconds=60),
        ends_at=now + timedelta(seconds=120),
        total_seconds=180,
        next_set_label="ベンチプレス 2セット目",
    )
    DbRestTimerRepository(db_session).save_rest_timer(timer)
    return timer


class TestCreatePushSubscription:
    @pytest.mark.parametrize(
        "endpoint",
        [
            pytest.param("https://web.push.apple.com/QGuQyavXutnMH", id="Apple"),
            pytest.param("https://fcm.googleapis.com/fcm/send/dpH5lCsTSSM:APA91bH", id="FCM"),
            pytest.param("https://updates.push.services.mozilla.com/wpush/v2/gAAAAABn", id="Mozilla"),
            pytest.param("https://wns2-par02p.notify.windows.com/w/?token=BQYAAAB", id="Windows"),
        ],
    )
    def test_Web_Push_のサービスの購読は登録できる(self, client: TestClient, endpoint: str) -> None:
        resp = client.post(
            "/api/rest-timer/push-subscriptions", json={"endpoint": endpoint, "p256dh": P256DH, "auth": AUTH}
        )

        assert resp.status_code == 204

    @pytest.mark.parametrize(
        ("body", "field"),
        [
            pytest.param(
                {"endpoint": "http://web.push.apple.com/QGuQyavXutnMH", "p256dh": P256DH, "auth": AUTH},
                "endpoint",
                id="https でない",
            ),
            pytest.param(
                {"endpoint": "https://internal.example/hook", "p256dh": P256DH, "auth": AUTH},
                "endpoint",
                id="Web Push のサービス以外のホスト",
            ),
            pytest.param(
                {"endpoint": "https://fcm.googleapis.com.internal.example/hook", "p256dh": P256DH, "auth": AUTH},
                "endpoint",
                id="Web Push のサービスのホスト名で始まる別のホスト",
            ),
            pytest.param(
                {"endpoint": "https://internal.example\\@fcm.googleapis.com/hook", "p256dh": P256DH, "auth": AUTH},
                "endpoint",
                id="バックスラッシュでホストを偽る",
            ),
            pytest.param(
                {"endpoint": ENDPOINT + "a" * (501 - len(ENDPOINT)), "p256dh": P256DH, "auth": AUTH},
                "endpoint",
                id="endpoint が 500 字より長い",
            ),
            pytest.param(
                {"endpoint": ENDPOINT, "p256dh": P256DH[:-4], "auth": AUTH},
                "p256dh",
                id="p256dh が 65 バイトより短い",
            ),
            pytest.param(
                {"endpoint": ENDPOINT, "p256dh": _b64url(b"\x04" + b"\x01" * 65), "auth": AUTH},
                "p256dh",
                id="p256dh が 65 バイトより長い",
            ),
            pytest.param(
                {"endpoint": ENDPOINT, "p256dh": _b64url(b"\x04" + b"\x01" * 64), "auth": AUTH},
                "p256dh",
                id="p256dh が P-256 の曲線上の点でない",
            ),
            pytest.param(
                {"endpoint": ENDPOINT, "p256dh": P256DH, "auth": _b64url(b"\x02" * 15)},
                "auth",
                id="auth が 16 バイトより短い",
            ),
            pytest.param(
                {"endpoint": ENDPOINT, "p256dh": P256DH, "auth": AUTH + "AA"},
                "auth",
                id="auth が 16 バイトより長い",
            ),
            pytest.param(
                {"endpoint": ENDPOINT, "p256dh": P256DH, "auth": "!" * 22},
                "auth",
                id="auth が base64url でない",
            ),
        ],
    )
    def test_https_でないか_Web_Push_のサービス以外か長さの合わない鍵の購読は_422(
        self, client: TestClient, body: dict[str, str], field: str
    ) -> None:
        resp = client.post("/api/rest-timer/push-subscriptions", json=body)

        assert resp.status_code == 422
        assert [error["loc"] for error in resp.json()["detail"]] == [["body", field]]


class TestGetRestTimer:
    def test_動いているタイマーを開き直すと開始したときと同じ終了時刻で返す(
        self, client: TestClient, db_session: Session
    ) -> None:
        timer = _save_running_timer(db_session)

        resp = client.get("/api/rest-timer")

        assert resp.status_code == 200
        assert datetime.fromisoformat(resp.json()["ends_at"]) == timer.ends_at


class TestCreateRestTimer:
    def test_通知を予約できなければ_503_で固定の文言を返す(self, failing_job_queue_client: TestClient) -> None:
        resp = failing_job_queue_client.post(
            "/api/rest-timer", json={"seconds": 180, "next_set_label": "ベンチプレス 2セット目"}
        )

        assert resp.status_code == 503
        assert resp.json() == {"detail": "レストタイマーを開始できませんでした"}


class TestExtendRestTimer:
    def test_動いているタイマーが無ければ_404(self, job_queue_client: TestClient) -> None:
        resp = job_queue_client.post("/api/rest-timer/extend", json={"seconds": 30})

        assert resp.status_code == 404
        assert resp.json() == {"detail": "動いているレストタイマーがありません"}

    def test_通知を予約できなければ_503_で固定の文言を返す(
        self, failing_job_queue_client: TestClient, db_session: Session
    ) -> None:
        _save_running_timer(db_session)

        resp = failing_job_queue_client.post("/api/rest-timer/extend", json={"seconds": 30})

        assert resp.status_code == 503
        assert resp.json() == {"detail": "レストタイマーを延長できませんでした"}


class _FailingJobQueue:
    def enqueue(
        self,
        task_name: str,
        *,
        countdown_seconds: int | None = None,
        expires_seconds: int | None = None,
        **kwargs: str | int,
    ) -> str:
        raise JobQueueUnavailable(f"ジョブを登録できませんでした: task_name={task_name}")
