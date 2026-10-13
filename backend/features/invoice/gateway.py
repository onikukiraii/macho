from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from common.errors import RenderError
from features.invoice._pure import build_invoice_lines
from features.invoice.types import Invoice, InvoiceAmount

LINE_HEIGHT = 18
TOP_MARGIN = 60
LEFT_MARGIN = 50


class ReportLabPdfRenderer:
    def render(self, invoice: Invoice, amount: InvoiceAmount) -> bytes:
        try:
            buffer = BytesIO()
            canvas = Canvas(buffer, pagesize=A4)
            _, height = A4
            for index, text in enumerate(build_invoice_lines(invoice, amount)):
                canvas.drawString(LEFT_MARGIN, height - TOP_MARGIN - index * LINE_HEIGHT, text)
            canvas.save()
            return buffer.getvalue()
        except Exception as e:
            raise RenderError(f"pdf render failed: invoice_id={invoice.id}") from e
