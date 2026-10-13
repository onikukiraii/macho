import logging
import math
from collections import Counter
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from common.errors import NotFound
from common.gateway.protocol import JobQueue
from features.rest_timer._pure import build_rest_finished_message, from_epoch_microseconds, to_epoch_microseconds
from features.rest_timer.protocol import PushSender, RestTimerRepository
from features.rest_timer.types import PushResult, RestTimer

logger = logging.getLogger(__name__)

NOTIFY_REST_FINISHED_TASK_NAME = "rest_timer.notify_rest_finished"
# Celery の expires は送信時刻を起点に数えるため、実行予定の時刻に猶予を足す
NOTIFICATION_EXPIRY_GRACE_SECONDS = 60


def register_push_subscription(repo: RestTimerRepository, *, endpoint: str, p256dh: str, auth: str) -> None:
    repo.save_push_subscription(endpoint=endpoint, p256dh=p256dh, auth=auth)


def get_rest_timer(repo: RestTimerRepository) -> RestTimer | None:
    timer = repo.get_rest_timer()
    if timer is None or timer.ends_at <= datetime.now(UTC):
        return None
    return timer


def start_rest_timer(repo: RestTimerRepository, job_queue: JobQueue, *, seconds: int, next_set_label: str) -> RestTimer:
    started_at = datetime.now(UTC)
    timer = RestTimer(
        uid=str(uuid4()),
        started_at=started_at,
        ends_at=started_at + timedelta(seconds=seconds),
        total_seconds=seconds,
        next_set_label=next_set_label,
    )
    _enqueue_notification(job_queue, timer, now=started_at)
    repo.save_rest_timer(timer)
    return timer


def extend_rest_timer(repo: RestTimerRepository, job_queue: JobQueue, *, seconds: int) -> RestTimer:
    now = datetime.now(UTC)
    timer = repo.get_rest_timer_for_update()
    if timer is None or timer.ends_at <= now:
        raise NotFound("動いているレストタイマーがありません")
    extended = replace(
        timer,
        ends_at=timer.ends_at + timedelta(seconds=seconds),
        total_seconds=timer.total_seconds + seconds,
    )
    _enqueue_notification(job_queue, extended, now=now)
    repo.save_rest_timer(extended)
    return extended


def stop_rest_timer(repo: RestTimerRepository) -> None:
    repo.delete_rest_timer()


def notify_rest_finished(
    repo: RestTimerRepository, push_sender: PushSender, *, uid: str, ends_at: int, next_set_label: str
) -> None:
    # 停止・延長・置き換えのあとに残った予約と、同じ予約の再実行は、この削除が0行になって通知しない
    is_deleted = repo.delete_finished_rest_timer(uid=uid, ends_at=from_epoch_microseconds(ends_at))
    if not is_deleted:
        return

    message = build_rest_finished_message(next_set_label)
    subscriptions = repo.list_push_subscriptions()
    result_counts: Counter[PushResult] = Counter()
    for subscription in subscriptions:
        result = push_sender.send(subscription, title=message.title, body=message.body)
        result_counts[result] += 1
        if result is PushResult.expired:
            repo.delete_push_subscription(subscription.id)

    log = logger.warning if result_counts[PushResult.failed] > 0 else logger.info
    log(
        "レスト終了を通知しました: uid=%s devices=%d delivered=%d expired=%d failed=%d",
        uid,
        len(subscriptions),
        result_counts[PushResult.delivered],
        result_counts[PushResult.expired],
        result_counts[PushResult.failed],
    )


def _enqueue_notification(job_queue: JobQueue, timer: RestTimer, *, now: datetime) -> None:
    countdown_seconds = math.ceil((timer.ends_at - now).total_seconds())
    job_queue.enqueue(
        NOTIFY_REST_FINISHED_TASK_NAME,
        countdown_seconds=countdown_seconds,
        expires_seconds=countdown_seconds + NOTIFICATION_EXPIRY_GRACE_SECONDS,
        uid=timer.uid,
        # 通知のジョブは DB の終了時刻と一致したときだけ通知するため、マイクロ秒まで渡す
        ends_at=to_epoch_microseconds(timer.ends_at),
        next_set_label=timer.next_set_label,
    )
