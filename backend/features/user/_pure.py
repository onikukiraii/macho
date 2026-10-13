from common.errors import BusinessRuleViolation


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_name(name: str) -> None:
    if not name.strip():
        raise BusinessRuleViolation("名前を入力してください。")
