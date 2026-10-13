from features.review.prompts import REVIEW_TEMPLATE
from features.review.types import FindingOutput, ReviewFinding


def build_review_prompt(contract_text: str, rules: list[str]) -> str:
    return REVIEW_TEMPLATE.format(
        contract_text=contract_text,
        rules="\n".join(f"- {rule}" for rule in rules),
    )


def to_findings(outputs: list[FindingOutput]) -> list[ReviewFinding]:
    return [ReviewFinding(severity=output.severity, comment=output.comment, quote=output.quote) for output in outputs]
