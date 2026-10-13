import pytest

from common.errors import BusinessRuleViolation
from features.user._pure import normalize_email, validate_name


class TestNormalizeEmail:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Test@Example.com", "test@example.com"),
            ("  test@example.com  ", "test@example.com"),
        ],
    )
    def test_大文字と前後の空白を落とす(self, raw: str, expected: str) -> None:
        assert normalize_email(raw) == expected


class TestValidateName:
    def test_空白だけの名前は弾く(self) -> None:
        with pytest.raises(BusinessRuleViolation):
            validate_name("   ")

    def test_名前があれば通る(self) -> None:
        validate_name("田中太郎")
