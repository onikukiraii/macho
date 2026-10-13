import base64
from collections.abc import Callable

import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import ec
from http_ece import ECEException
from pywebpush import WebPushException

from features.rest_timer.gateway import WebPushSender
from features.rest_timer.types import PushResult, PushSubscription

SUBSCRIPTION = PushSubscription(id=1, endpoint="https://web.push.apple.com/iphone", p256dh="p256dh", auth="auth")


def _vapid_private_key() -> str:
    private_value = ec.generate_private_key(ec.SECP256R1()).private_numbers().private_value
    return base64.urlsafe_b64encode(private_value.to_bytes(32, "big")).decode().rstrip("=")


def _response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    return response


def _webpush_returning(outcome: requests.Response | Exception) -> Callable[..., requests.Response]:
    def _webpush(**_: object) -> requests.Response:
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return _webpush


class TestSend:
    @pytest.mark.parametrize(
        ("outcome", "expected"),
        [
            pytest.param(_response(201), PushResult.delivered, id="201"),
            pytest.param(WebPushException("Not Found", response=_response(404)), PushResult.expired, id="404"),
            pytest.param(WebPushException("Gone", response=_response(410)), PushResult.expired, id="410"),
            pytest.param(WebPushException("Server Error", response=_response(500)), PushResult.failed, id="500"),
            pytest.param(requests.ConnectionError(), PushResult.failed, id="接続できない"),
            pytest.param(ValueError("Invalid EC key."), PushResult.failed, id="鍵が曲線上の点でない"),
            pytest.param(ECEException("Invalid salt"), PushResult.failed, id="暗号化できない"),
        ],
    )
    def test_Web_Push_のサービスの応答を配信済みか失効か失敗に分類する(
        self, monkeypatch: pytest.MonkeyPatch, outcome: requests.Response | Exception, expected: PushResult
    ) -> None:
        monkeypatch.setattr("features.rest_timer.gateway.webpush", _webpush_returning(outcome))
        sender = WebPushSender(vapid_private_key=_vapid_private_key(), vapid_subject="mailto:test@example.com")

        result = sender.send(SUBSCRIPTION, title="レスト終了", body="ベンチプレス 2セット目")

        assert result is expected

    @pytest.mark.parametrize(
        "error",
        [
            pytest.param(
                WebPushException(f"Push failed: 500 {SUBSCRIPTION.endpoint}", response=_response(500)), id="500"
            ),
            pytest.param(
                requests.ConnectionError(f"Max retries exceeded with url: {SUBSCRIPTION.endpoint}"), id="接続できない"
            ),
        ],
    )
    def test_送信できなかったログに端末の_endpoint_を出さない(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, error: Exception
    ) -> None:
        monkeypatch.setattr("features.rest_timer.gateway.webpush", _webpush_returning(error))
        sender = WebPushSender(vapid_private_key=_vapid_private_key(), vapid_subject="mailto:test@example.com")

        sender.send(SUBSCRIPTION, title="レスト終了", body="ベンチプレス 2セット目")

        assert (len(caplog.records), SUBSCRIPTION.endpoint in caplog.text) == (1, False)
