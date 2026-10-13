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
