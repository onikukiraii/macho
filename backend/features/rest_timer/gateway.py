import json
import logging

from http_ece import ECEException
from py_vapid import Vapid
from pywebpush import WebPushException, webpush
from requests import RequestException

from features.rest_timer.types import PushResult, PushSubscription

logger = logging.getLogger(__name__)

# 終了の通知は遅れて届いても役に立たないため、端末に届けられないまま60秒経ったら破棄させる
_TTL_SECONDS = 60
_TIMEOUT_SECONDS = 10


class WebPushSender:
    def __init__(self, *, vapid_private_key: str, vapid_subject: str) -> None:
        self._vapid = Vapid.from_string(vapid_private_key)
        self._vapid_subject = vapid_subject

    def send(self, subscription: PushSubscription, *, title: str, body: str) -> PushResult:
        # 失敗は例外にせず結果として返す。呼び出し側は全端末へ順に送るため、1台の失敗でほかの端末への通知を止めない
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
        # 例外の文言とスタックトレースには endpoint の URL が入り、URL は端末へ通知を送れるトークンを兼ねる。
        # そのため logger.exception は使わず、購読の ID、例外の型名、HTTP ステータスに絞って出す
        except WebPushException as e:
            if e.status_code in (404, 410):
                return PushResult.expired
            logger.warning(
                "Web Push を送信できませんでした: subscription_id=%d error=%s status=%s",
                subscription.id,
                type(e).__name__,
                e.status_code,
            )
            return PushResult.failed
        # ValueError と ECEException は、登録済みの鍵で通知を暗号化できないときに出る
        except (RequestException, ValueError, ECEException) as e:
            logger.warning(
                "Web Push を送信できませんでした: subscription_id=%d error=%s", subscription.id, type(e).__name__
            )
            return PushResult.failed
        return PushResult.delivered
