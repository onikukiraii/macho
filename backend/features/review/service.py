from uuid import uuid4

from common.errors import LLMError
from common.gateway.protocol import LLM
from features.review._pure import build_review_prompt, to_findings
from features.review.prompts import REVIEW_SYSTEM
from features.review.protocol import ReviewRepository
from features.review.types import Review, ReviewOutput


def list_reviews(repo: ReviewRepository) -> list[Review]:
    return repo.list_all()


def get_review(repo: ReviewRepository, *, uid: str) -> Review:
    return repo.get(uid)


def request_review(repo: ReviewRepository, llm: LLM, *, contract_text: str, rules: list[str]) -> Review:
    uid = str(uuid4())
    repo.create_running(uid=uid, contract_text=contract_text)

    try:
        output = llm.complete(
            system=REVIEW_SYSTEM,
            prompt=build_review_prompt(contract_text, rules),
            output=ReviewOutput,
            trace_id=uid,
        )
    except LLMError:
        repo.save_failed(uid)
        raise

    return repo.save_succeeded(uid, summary=output.summary, findings=to_findings(output.findings))
