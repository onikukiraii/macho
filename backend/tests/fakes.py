from features.rest_timer.types import PushResult, PushSubscription


class FakeJobQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, dict[str, str | int]]] = []
        self.countdown_seconds: list[int | None] = []
        self.expires_seconds: list[int | None] = []

    def enqueue(
        self,
        task_name: str,
        *,
        countdown_seconds: int | None = None,
        expires_seconds: int | None = None,
        **kwargs: str | int,
    ) -> str:
        self.enqueued.append((task_name, kwargs))
        self.countdown_seconds.append(countdown_seconds)
        self.expires_seconds.append(expires_seconds)
        return f"job-{len(self.enqueued)}"


class FakePushSender:
    def __init__(self, results: dict[str, PushResult] | None = None) -> None:
        self.sent: list[tuple[str, str, str]] = []
        self._results = results if results is not None else {}

    def send(self, subscription: PushSubscription, *, title: str, body: str) -> PushResult:
        self.sent.append((subscription.endpoint, title, body))
        return self._results.get(subscription.endpoint, PushResult.delivered)
