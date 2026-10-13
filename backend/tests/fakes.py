from datetime import UTC, datetime

from pydantic import BaseModel

from common.errors import Conflict, NotFound
from features.invoice.types import Invoice, InvoiceAmount, InvoiceLine, InvoiceStatus
from features.review.types import Review, ReviewFinding, ReviewStatus
from features.user.types import User


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, body: bytes, content_type: str) -> None:
        self.objects[key] = body

    def get(self, key: str) -> bytes:
        if key not in self.objects:
            raise NotFound(f"object not found: key={key}")
        return self.objects[key]

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return f"https://example.test/{key}"


class FakeLLM:
    def __init__(self, responses: list[BaseModel]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []
        self.trace_ids: list[str] = []

    def complete[T: BaseModel](self, *, system: str, prompt: str, output: type[T], trace_id: str) -> T:
        self.prompts.append(prompt)
        self.trace_ids.append(trace_id)
        response = self.responses.pop(0)
        if not isinstance(response, output):
            raise TypeError(f"FakeLLM に積んだ応答が {output.__name__} ではありません。")
        return response


class FakeJobQueue:
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, dict[str, str | int]]] = []

    def enqueue(self, task_name: str, **kwargs: str | int) -> str:
        self.enqueued.append((task_name, kwargs))
        return f"job-{len(self.enqueued)}"


class FakePdfRenderer:
    def __init__(self) -> None:
        self.rendered: list[tuple[int, InvoiceAmount]] = []

    def render(self, invoice: Invoice, amount: InvoiceAmount) -> bytes:
        self.rendered.append((invoice.id, amount))
        return b"%PDF-fake"


class InMemoryUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self.users = list(users or [])

    def list_all(self) -> list[User]:
        return list(self.users)

    def create(self, *, name: str, email: str) -> User:
        if any(user.email == email for user in self.users):
            raise Conflict(f"email はすでに登録されています: email={email}")
        user = User(id=len(self.users) + 1, name=name, email=email, created_at=datetime.now(UTC))
        self.users.append(user)
        return user


class InMemoryInvoiceRepository:
    def __init__(self, invoices: list[Invoice] | None = None) -> None:
        self.invoices = {invoice.id: invoice for invoice in invoices or []}

    def get(self, invoice_id: int) -> Invoice:
        if invoice_id not in self.invoices:
            raise NotFound(f"invoice が見つかりません: invoice_id={invoice_id}")
        return self.invoices[invoice_id]

    def list_all(self) -> list[Invoice]:
        return [self.invoices[key] for key in sorted(self.invoices)]

    def create(self, *, customer_name: str, discount_rate: float, lines: list[InvoiceLine]) -> Invoice:
        invoice = Invoice(
            id=len(self.invoices) + 1,
            customer_name=customer_name,
            status=InvoiceStatus.draft,
            discount_rate=discount_rate,
            lines=lines,
            total=None,
            issued_at=None,
        )
        self.invoices[invoice.id] = invoice
        return invoice

    def save_issued(self, invoice: Invoice, total: int, *, issued_at: datetime) -> Invoice:
        issued = Invoice(
            id=invoice.id,
            customer_name=invoice.customer_name,
            status=InvoiceStatus.issued,
            discount_rate=invoice.discount_rate,
            lines=invoice.lines,
            total=total,
            issued_at=issued_at,
        )
        self.invoices[invoice.id] = issued
        return issued


class InMemoryReviewRepository:
    def __init__(self, reviews: list[Review] | None = None) -> None:
        self.reviews = {review.uid: review for review in reviews or []}

    def get(self, uid: str) -> Review:
        if uid not in self.reviews:
            raise NotFound(f"review が見つかりません: uid={uid}")
        return self.reviews[uid]

    def list_all(self) -> list[Review]:
        return [self.reviews[key] for key in sorted(self.reviews)]

    def create_running(self, *, uid: str, contract_text: str) -> Review:
        review = Review(
            uid=uid,
            status=ReviewStatus.running,
            contract_text=contract_text,
            summary=None,
            findings=[],
            created_at=datetime.now(UTC),
        )
        self.reviews[uid] = review
        return review

    def save_succeeded(self, uid: str, *, summary: str, findings: list[ReviewFinding]) -> Review:
        return self._replace(uid, status=ReviewStatus.succeeded, summary=summary, findings=findings)

    def save_failed(self, uid: str) -> Review:
        return self._replace(uid, status=ReviewStatus.failed, summary=None, findings=[])

    def _replace(
        self,
        uid: str,
        *,
        status: ReviewStatus,
        summary: str | None,
        findings: list[ReviewFinding],
    ) -> Review:
        current = self.get(uid)
        updated = Review(
            uid=current.uid,
            status=status,
            contract_text=current.contract_text,
            summary=summary,
            findings=findings,
            created_at=current.created_at,
        )
        self.reviews[uid] = updated
        return updated
