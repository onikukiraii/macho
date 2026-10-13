from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from common.db.entities import PushSubscriptionRow, RestTimerRow
from features.rest_timer.repository import DbRestTimerRepository
from features.rest_timer.types import RestTimer

IPHONE = "https://web.push.apple.com/iphone"


def _timer(uid: str, *, seconds: int) -> RestTimer:
    now = datetime.now(UTC)
    return RestTimer(
        uid=uid,
        started_at=now,
        ends_at=now + timedelta(seconds=seconds),
        total_seconds=seconds,
        next_set_label="ベンチプレス 2セット目",
    )


class TestSavePushSubscription:
    def test_同じ端末の登録が並行して先に保存されていれば鍵を上書きする(self, db_session: Session) -> None:
        DbRestTimerRepository(db_session).save_push_subscription(endpoint=IPHONE, p256dh="old-p256dh", auth="old-auth")
        repo = _SubscriptionRacingRepository(db_session)

        repo.save_push_subscription(endpoint=IPHONE, p256dh="new-p256dh", auth="new-auth")

        assert [(s.endpoint, s.p256dh, s.auth) for s in repo.list_push_subscriptions()] == [
            (IPHONE, "new-p256dh", "new-auth")
        ]


class TestSaveRestTimer:
    def test_並行した開始が先に保存されていれば置き換える(self, db_session: Session) -> None:
        DbRestTimerRepository(db_session).save_rest_timer(_timer("6b1f0c2a-3d4e-4f5a-8b9c-0d1e2f3a4b5c", seconds=180))
        repo = _RestTimerRacingRepository(db_session)
        second = _timer("9e8d7c6b-5a4f-4e3d-8c2b-1a0f9e8d7c6b", seconds=90)

        repo.save_rest_timer(second)

        assert repo.get_rest_timer() == second


class _SubscriptionRacingRepository(DbRestTimerRepository):
    """行が無いことを確かめたあとに、並行した登録が同じ endpoint を保存した状態を作る。"""

    _raced = False

    def _get_push_subscription_row(self, endpoint: str) -> PushSubscriptionRow | None:
        if not self._raced:
            self._raced = True
            return None
        return super()._get_push_subscription_row(endpoint)


class _RestTimerRacingRepository(DbRestTimerRepository):
    """行が無いことを確かめたあとに、並行した開始がタイマーを保存した状態を作る。"""

    _raced = False

    def _get_rest_timer_row(self) -> RestTimerRow | None:
        if not self._raced:
            self._raced = True
            return None
        return super()._get_rest_timer_row()
