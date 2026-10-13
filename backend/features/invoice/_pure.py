from common.errors import BusinessRuleViolation
from features.invoice.types import Invoice, InvoiceAmount, InvoiceLine, InvoiceStatus

TAX_RATE = 0.1
DISCOUNT_THRESHOLD = 100_000


def calculate_amount(lines: list[InvoiceLine], discount_rate: float) -> InvoiceAmount:
    subtotal = sum(line.unit_price * line.quantity for line in lines)
    discount = int(subtotal * discount_rate) if subtotal >= DISCOUNT_THRESHOLD else 0
    taxable = subtotal - discount
    tax = int(taxable * TAX_RATE)
    return InvoiceAmount(subtotal=subtotal, discount=discount, tax=tax, total=taxable + tax)


def validate_issuable(status: InvoiceStatus, amount: InvoiceAmount) -> None:
    if status is not InvoiceStatus.draft:
        raise BusinessRuleViolation("下書き以外は発行できません。")
    if amount.total <= 0:
        raise BusinessRuleViolation("合計が0以下の請求書は発行できません。")


def invoice_object_key(invoice_id: int) -> str:
    return f"invoices/{invoice_id}.pdf"


def build_invoice_lines(invoice: Invoice, amount: InvoiceAmount) -> list[str]:
    rows = [f"請求書 #{invoice.id}", f"宛先: {invoice.customer_name}", ""]
    rows += [f"{line.description}  {line.unit_price:,} x {line.quantity}" for line in invoice.lines]
    rows += [
        "",
        f"小計: {amount.subtotal:,}",
        f"割引: {amount.discount:,}",
        f"消費税: {amount.tax:,}",
        f"合計: {amount.total:,}",
    ]
    return rows
