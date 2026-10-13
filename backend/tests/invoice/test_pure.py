import pytest

from common.errors import BusinessRuleViolation
from features.invoice._pure import build_invoice_lines, calculate_amount, invoice_object_key, validate_issuable
from features.invoice.types import Invoice, InvoiceAmount, InvoiceLine, InvoiceStatus


def _line(unit_price: int, quantity: int = 1) -> InvoiceLine:
    return InvoiceLine(description="作業費", unit_price=unit_price, quantity=quantity)


class TestCalculateAmount:
    def test_割引は10万円以上で効く(self) -> None:
        amount = calculate_amount([_line(50_000, 2)], 0.1)

        assert amount.subtotal == 100_000
        assert amount.discount == 10_000

    def test_割引は10万円未満では効かない(self) -> None:
        assert calculate_amount([_line(99_999)], 0.1).discount == 0

    def test_消費税は割引後の金額にかかる(self) -> None:
        amount = calculate_amount([_line(100_000)], 0.1)

        assert amount.tax == 9_000
        assert amount.total == 99_000

    def test_明細が空なら合計は0(self) -> None:
        assert calculate_amount([], 0.1) == InvoiceAmount(subtotal=0, discount=0, tax=0, total=0)


class TestValidateIssuable:
    def test_下書きなら通る(self) -> None:
        validate_issuable(InvoiceStatus.draft, InvoiceAmount(subtotal=100, discount=0, tax=10, total=110))

    @pytest.mark.parametrize("status", [InvoiceStatus.issued, InvoiceStatus.paid])
    def test_下書き以外は弾く(self, status: InvoiceStatus) -> None:
        with pytest.raises(BusinessRuleViolation):
            validate_issuable(status, InvoiceAmount(subtotal=100, discount=0, tax=10, total=110))

    def test_合計が0なら弾く(self) -> None:
        with pytest.raises(BusinessRuleViolation):
            validate_issuable(InvoiceStatus.draft, InvoiceAmount(subtotal=0, discount=0, tax=0, total=0))


class TestInvoiceObjectKey:
    def test_id_からキーを作る(self) -> None:
        assert invoice_object_key(42) == "invoices/42.pdf"


class TestBuildInvoiceLines:
    def test_宛先と明細と合計が並ぶ(self) -> None:
        invoice = Invoice(
            id=1,
            customer_name="株式会社テスト",
            status=InvoiceStatus.draft,
            discount_rate=0.0,
            lines=[_line(1_000, 2)],
            total=None,
            issued_at=None,
        )
        amount = calculate_amount(invoice.lines, invoice.discount_rate)

        rows = build_invoice_lines(invoice, amount)

        assert rows[0] == "請求書 #1"
        assert rows[1] == "宛先: 株式会社テスト"
        assert "作業費  1,000 x 2" in rows
        assert rows[-1] == "合計: 2,200"
