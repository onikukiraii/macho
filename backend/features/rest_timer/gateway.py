import json
import logging

from py_vapid import Vapid
from pywebpush import WebPushException, webpush
from requests import RequestException

from features.rest_timer.types import PushResult, PushSubscription

logger = logging.getLogger(__name__)

# 終了の通知は数分で意味を失うため、端末に届けられない状態が続いたら破棄させる
_TTL_SECONDS = 60
_TIMEOUT_SECONDS = 10


class WebPushSender:
    def __init__(self, *, vapid_private_key: str, vapid_subject: str) -> None:
        self._vapid = Vapid.from_string(vapid_private_key)
        self._vapid_subject = vapid_subject

    def send(self, subscription: PushSubscription, *, title: str, body: str) -> PushResult:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps({"title": title, "body": body}, ensure_ascii=False),
                vapid_private_key=self._vapid,
                # webpush が aud と exp を書き足すため、呼び出しごとに新しい dict を渡す
                vapid_claims={"sub": self._vapid_subject},
                ttl=_TTL_SECONDS,
                timeout=_TIMEOUT_SECONDS,
            )
        except WebPushException as e:
            if e.status_code in (404, 410):
                return PushResult.expired
            logger.warning(
                "Web Push を送信できませんでした: subscription_id=%d status=%s", subscription.id, e.status_code
            )
            return PushResult.failed
        except RequestException as e:
            logger.warning(
                "Web Push を送信できませんでした: subscription_id=%d error=%s", subscription.id, type(e).__name__
            )
            return PushResult.failed
        return PushResult.delivered
