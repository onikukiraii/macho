from datetime import UTC, datetime, timedelta

import pymysql
import pytest
from sqlalchemy.exc import OperationalError
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
        assert repo._raced


class TestSaveRestTimer:
    def test_並行した開始が先に保存されていれば置き換える(self, db_session: Session) -> None:
        DbRestTimerRepository(db_session).save_rest_timer(_timer("6b1f0c2a-3d4e-4f5a-8b9c-0d1e2f3a4b5c", seconds=180))
        repo = _RestTimerRacingRepository(db_session)
        second = _timer("9e8d7c6b-5a4f-4e3d-8c2b-1a0f9e8d7c6b", seconds=90)

        repo.save_rest_timer(second)

        assert repo.get_rest_timer() == second
        assert repo._raced

    def test_並行した開始とデッドロックしたらやり直して保存する(self, db_session: Session) -> None:
        repo = _RestTimerLockFailingRepository(db_session, error_code=_MYSQL_DEADLOCK)
        timer = _timer("6b1f0c2a-3d4e-4f5a-8b9c-0d1e2f3a4b5c", seconds=180)

        repo.save_rest_timer(timer)

        assert repo.get_rest_timer() == timer
        assert repo._failed

    def test_デッドロック以外の_OperationalError_はそのまま送出する(self, db_session: Session) -> None:
        repo = _RestTimerLockFailingRepository(db_session, error_code=_MYSQL_LOST_CONNECTION)

        with pytest.raises(OperationalError):
            repo.save_rest_timer(_timer("6b1f0c2a-3d4e-4f5a-8b9c-0d1e2f3a4b5c", seconds=180))


# db_session は1本の接続しか持たず、2つのトランザクションを並行させられない。並行した側が先に書いた状態と
# MySQL のロックの失敗は、行を読む内部メソッドを差し替えて作る。差し替えたメソッドが呼ばれたことは各テストの
# 末尾で確かめ、メソッド名が変わって差し替えが外れたまま通るのを防ぐ
_MYSQL_DEADLOCK = 1213
_MYSQL_LOST_CONNECTION = 2013


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


class _RestTimerLockFailingRepository(DbRestTimerRepository):
    """行が無いことを確かめてから INSERT するまでの間に、MySQL がトランザクションを打ち切った状態を作る。"""

    _failed = False

    def __init__(self, session: Session, *, error_code: int) -> None:
        super().__init__(session)
        self._error_code = error_code

    def _get_rest_timer_row(self) -> RestTimerRow | None:
        if not self._failed:
            self._failed = True
            raise OperationalError("INSERT INTO rest_timers", None, pymysql.err.OperationalError(self._error_code))
        return super()._get_rest_timer_row()
