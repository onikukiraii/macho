from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from common.db.entities import PushSubscriptionRow, RestTimerRow
from features.rest_timer.types import PushSubscription, RestTimer

_MYSQL_DEADLOCK = 1213


class DbRestTimerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_push_subscription(self, *, endpoint: str, p256dh: str, auth: str) -> None:
        try:
            self._upsert_push_subscription(endpoint=endpoint, p256dh=p256dh, auth=auth)
        except IntegrityError:
            # 同じ端末の登録が並行すると、後の INSERT が一意制約に違反する。先に保存された行を上書きし直す
            self._session.rollback()
            self._upsert_push_subscription(endpoint=endpoint, p256dh=p256dh, auth=auth)

    def list_push_subscriptions(self) -> list[PushSubscription]:
        rows = self._session.execute(select(PushSubscriptionRow).order_by(PushSubscriptionRow.id)).scalars().all()
        return [PushSubscription(id=row.id, endpoint=row.endpoint, p256dh=row.p256dh, auth=row.auth) for row in rows]

    def delete_push_subscription(self, subscription_id: int) -> None:
        self._session.execute(delete(PushSubscriptionRow).where(PushSubscriptionRow.id == subscription_id))
        self._session.commit()

    def get_rest_timer(self) -> RestTimer | None:
        row = self._session.execute(select(RestTimerRow).where(RestTimerRow.slot == 1)).scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    def get_rest_timer_for_update(self) -> RestTimer | None:
        row = self._get_rest_timer_row()
        return _to_domain(row) if row is not None else None

    def save_rest_timer(self, timer: RestTimer) -> None:
        try:
            self._upsert_rest_timer(timer)
        except IntegrityError:
            # 行が無いときに開始が並行すると、後の INSERT が slot の一意制約に違反する。先に保存された行を置き換え直す
            self._session.rollback()
            self._upsert_rest_timer(timer)
        except OperationalError as e:
            # 行が無いときの開始が並行すると、REPEATABLE READ で互いの SELECT ... FOR UPDATE が取ったギャップロックに
            # INSERT が阻まれてデッドロックになる。打ち切られた側は、先の開始が保存した行を置き換え直す
            if e.orig is None or e.orig.args[0] != _MYSQL_DEADLOCK:
                raise
            self._session.rollback()
            self._upsert_rest_timer(timer)

    def delete_rest_timer(self) -> None:
        self._session.execute(delete(RestTimerRow))
        self._session.commit()

    def delete_finished_rest_timer(self, *, uid: str, ends_at: datetime) -> bool:
        result = self._session.connection().execute(
            delete(RestTimerRow).where(RestTimerRow.uid == uid, RestTimerRow.ends_at == ends_at)
        )
        self._session.commit()
        return result.rowcount > 0

    def _upsert_push_subscription(self, *, endpoint: str, p256dh: str, auth: str) -> None:
        row = self._get_push_subscription_row(endpoint)
        if row is None:
            row = PushSubscriptionRow(endpoint=endpoint)
            self._session.add(row)
        row.p256dh = p256dh
        row.auth = auth
        self._session.commit()

    def _upsert_rest_timer(self, timer: RestTimer) -> None:
        # rest_timers は slot の一意制約で1行に限るため、置き換えは同じ行の UPDATE で行う
        row = self._get_rest_timer_row()
        if row is None:
            row = RestTimerRow(slot=1)
            self._session.add(row)
        row.uid = timer.uid
        row.started_at = timer.started_at
        row.ends_at = timer.ends_at
        row.total_seconds = timer.total_seconds
        row.next_set_label = timer.next_set_label
        self._session.commit()

    def _get_push_subscription_row(self, endpoint: str) -> PushSubscriptionRow | None:
        statement = select(PushSubscriptionRow).where(PushSubscriptionRow.endpoint == endpoint)
        return self._session.execute(statement).scalar_one_or_none()

    def _get_rest_timer_row(self) -> RestTimerRow | None:
        # 延長・開始・停止・通知が同じ行を書き換えるため、読んでから書くまで行をロックする
        statement = select(RestTimerRow).where(RestTimerRow.slot == 1).with_for_update()
        return self._session.execute(statement).scalar_one_or_none()


def _to_domain(row: RestTimerRow) -> RestTimer:
    return RestTimer(
        uid=row.uid,
        started_at=row.started_at,
        ends_at=row.ends_at,
        total_seconds=row.total_seconds,
        next_set_label=row.next_set_label,
    )
