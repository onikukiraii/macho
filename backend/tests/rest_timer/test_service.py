import inspect
import math
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from common.errors import JobQueueUnavailable, NotFound
from features.rest_timer.repository import DbRestTimerRepository
from features.rest_timer.service import (
    NOTIFICATION_EXPIRY_GRACE_SECONDS,
    extend_rest_timer,
    get_rest_timer,
    notify_rest_finished,
    register_push_subscription,
    start_rest_timer,
    stop_rest_timer,
)
from features.rest_timer.types import PushResult, RestTimer
from tests.fakes import FakeJobQueue, FakePushSender
from worker.tasks import notify_rest_finished_task

IPHONE = "https://web.push.apple.com/iphone"
ANDROID = "https://fcm.googleapis.com/fcm/send/android"
WINDOWS = "https://wns2-par02p.notify.windows.com/w/?token=windows"


def _register(repo: DbRestTimerRepository, endpoint: str) -> None:
    register_push_subscription(repo, endpoint=endpoint, p256dh=f"p256dh-{endpoint}", auth=f"auth-{endpoint}")


def _save_finished_timer(repo: DbRestTimerRepository) -> RestTimer:
    now = datetime.now(UTC)
    timer = RestTimer(
        uid="0d6f2c1e-8a4b-4f3e-9c2d-1b5a7e9f0c3d",
        started_at=now - timedelta(seconds=181),
        ends_at=now - timedelta(seconds=1),
        total_seconds=180,
        next_set_label="ベンチプレス 2セット目",
    )
    repo.save_rest_timer(timer)
    return timer


def _run_job(repo: DbRestTimerRepository, push_sender: FakePushSender, job_queue: FakeJobQueue, index: int) -> None:
    _, kwargs = job_queue.enqueued[index]
    notify_rest_finished(
        repo,
        push_sender,
        uid=str(kwargs["uid"]),
        ends_at=int(kwargs["ends_at"]),
        next_set_label=str(kwargs["next_set_label"]),
    )


class TestRegisterPushSubscription:
    def test_同じ端末を再登録すると購読は1件のまま鍵が新しくなる(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        register_push_subscription(repo, endpoint=IPHONE, p256dh="old-p256dh", auth="old-auth")

        register_push_subscription(repo, endpoint=IPHONE, p256dh="new-p256dh", auth="new-auth")

        subscriptions = repo.list_push_subscriptions()
        assert [(s.endpoint, s.p256dh, s.auth) for s in subscriptions] == [(IPHONE, "new-p256dh", "new-auth")]


class TestStartRestTimer:
    def test_開始した秒数後に実行されるジョブを予約する(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        job_queue = FakeJobQueue()

        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")

        assert job_queue.countdown_seconds == [180]

    def test_予約するジョブは返した終了時刻に実行される(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        job_queue = FakeJobQueue()
        before = datetime.now(UTC)

        timer = start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")

        countdown = timedelta(seconds=job_queue.countdown_seconds[0] or 0)
        assert before + countdown <= timer.ends_at <= datetime.now(UTC) + countdown

    def test_予約するジョブの期限は実行予定より後で猶予の秒数を超えない(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        job_queue = FakeJobQueue()

        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")

        assert 180 < (job_queue.expires_seconds[0] or 0) <= 180 + NOTIFICATION_EXPIRY_GRACE_SECONDS

    def test_予約するジョブは_worker_に登録した通知タスクを指す(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        job_queue = FakeJobQueue()

        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")

        assert [task_name for task_name, _ in job_queue.enqueued] == [notify_rest_finished_task.name]

    def test_予約するジョブの引数は_worker_の通知タスクの引数と一致する(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        job_queue = FakeJobQueue()

        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")

        _, kwargs = job_queue.enqueued[0]
        bound = inspect.signature(notify_rest_finished_task.run).bind(**kwargs)
        assert bound.arguments == kwargs

    def test_動いている間にもう一度開始すると前のタイマーを置き換える(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        job_queue = FakeJobQueue()
        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")

        second = start_rest_timer(repo, job_queue, seconds=90, next_set_label="ラットプルダウン 1セット目")

        assert get_rest_timer(repo) == second

    def test_通知を予約できなければタイマーを保存しない(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)

        with pytest.raises(JobQueueUnavailable):
            start_rest_timer(repo, _FailingJobQueue(), seconds=180, next_set_label="ベンチプレス 2セット目")

        assert get_rest_timer(repo) is None


class TestGetRestTimer:
    def test_終了時刻を過ぎたタイマーは返さない(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        _save_finished_timer(repo)

        assert get_rest_timer(repo) is None


class TestExtendRestTimer:
    def test_延長すると終了時刻が延長した秒数だけ延びる(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        started = start_rest_timer(repo, FakeJobQueue(), seconds=180, next_set_label="ベンチプレス 2セット目")

        extend_rest_timer(repo, FakeJobQueue(), seconds=30)

        timer = get_rest_timer(repo)
        assert timer is not None
        assert timer.ends_at - started.ends_at == timedelta(seconds=30)

    def test_延長すると延びた終了時刻に実行されるジョブを予約する(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        job_queue = FakeJobQueue()
        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")
        before = datetime.now(UTC)

        extended = extend_rest_timer(repo, job_queue, seconds=30)

        after = datetime.now(UTC)
        assert (
            math.ceil((extended.ends_at - after).total_seconds())
            <= (job_queue.countdown_seconds[1] or 0)
            <= math.ceil((extended.ends_at - before).total_seconds())
        )

    def test_終了時刻を過ぎたタイマーは延長できない(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        _save_finished_timer(repo)

        with pytest.raises(NotFound):
            extend_rest_timer(repo, FakeJobQueue(), seconds=30)

    def test_通知を予約できなければ延長を保存しない(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        started = start_rest_timer(repo, FakeJobQueue(), seconds=180, next_set_label="ベンチプレス 2セット目")

        with pytest.raises(JobQueueUnavailable):
            extend_rest_timer(repo, _FailingJobQueue(), seconds=30)

        assert get_rest_timer(repo) == started


class TestNotifyRestFinished:
    def test_終了時にタイマーが残っていれば登録済みの全端末へ通知する(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        _register(repo, IPHONE)
        _register(repo, ANDROID)
        job_queue = FakeJobQueue()
        push_sender = FakePushSender()
        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")

        _run_job(repo, push_sender, job_queue, 0)

        assert push_sender.sent == [
            (IPHONE, "レスト終了", "ベンチプレス 2セット目"),
            (ANDROID, "レスト終了", "ベンチプレス 2セット目"),
        ]

    def test_延長すると前の終了時刻では通知せず延びた終了時刻に通知する(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        _register(repo, IPHONE)
        job_queue = FakeJobQueue()
        push_sender = FakePushSender()
        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")
        extend_rest_timer(repo, job_queue, seconds=30)

        _run_job(repo, push_sender, job_queue, 0)
        assert push_sender.sent == []

        _run_job(repo, push_sender, job_queue, 1)
        assert [endpoint for endpoint, _, _ in push_sender.sent] == [IPHONE]

    def test_置き換えると前のタイマーの終了時刻では通知しない(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        _register(repo, IPHONE)
        job_queue = FakeJobQueue()
        push_sender = FakePushSender()
        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")
        start_rest_timer(repo, job_queue, seconds=90, next_set_label="ラットプルダウン 1セット目")

        _run_job(repo, push_sender, job_queue, 0)

        assert push_sender.sent == []

    def test_停止すると終了時刻になっても通知しない(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        _register(repo, IPHONE)
        job_queue = FakeJobQueue()
        push_sender = FakePushSender()
        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")
        stop_rest_timer(repo)

        _run_job(repo, push_sender, job_queue, 0)

        assert push_sender.sent == []

    def test_同じ通知のジョブが2回実行されても通知は1回(self, db_session: Session) -> None:
        repo = DbRestTimerRepository(db_session)
        _register(repo, IPHONE)
        job_queue = FakeJobQueue()
        push_sender = FakePushSender()
        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")

        _run_job(repo, push_sender, job_queue, 0)
        _run_job(repo, push_sender, job_queue, 0)

        assert [endpoint for endpoint, _, _ in push_sender.sent] == [IPHONE]

    @pytest.mark.parametrize(
        ("result", "remaining"),
        [
            pytest.param(PushResult.expired, [IPHONE, WINDOWS], id="失効"),
            pytest.param(PushResult.failed, [IPHONE, ANDROID, WINDOWS], id="一時的な失敗"),
        ],
    )
    def test_失効した端末の購読は削除し失敗した端末があってもほかの端末へ送る(
        self, db_session: Session, result: PushResult, remaining: list[str]
    ) -> None:
        repo = DbRestTimerRepository(db_session)
        _register(repo, IPHONE)
        _register(repo, ANDROID)
        _register(repo, WINDOWS)
        job_queue = FakeJobQueue()
        push_sender = FakePushSender(results={ANDROID: result})
        start_rest_timer(repo, job_queue, seconds=180, next_set_label="ベンチプレス 2セット目")

        _run_job(repo, push_sender, job_queue, 0)

        assert [endpoint for endpoint, _, _ in push_sender.sent] == [IPHONE, ANDROID, WINDOWS]
        assert [s.endpoint for s in repo.list_push_subscriptions()] == remaining


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
