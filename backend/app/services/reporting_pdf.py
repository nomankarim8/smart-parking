from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings


def _register_configured_font() -> str:
    font_path = settings.PDF_FONT_PATH.strip()
    if not font_path:
        return "Helvetica"
    resolved = Path(font_path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Configured PDF font does not exist: {resolved}")
    font_name = "SmartParkingConfigured"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, str(resolved)))
    return font_name


def build_parking_history_pdf(
    *,
    rows: list[dict],
    start_date: str,
    end_date: str,
    filters: dict[str, str],
    generated_at: datetime,
) -> bytes:
    font_name = _register_configured_font()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="Smart Parking Session History",
        author=settings.PROJECT_NAME,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ParkingReportTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=19,
        leading=23,
        textColor=colors.HexColor("#172554"),
        alignment=TA_LEFT,
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "ParkingReportBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8,
        leading=11,
    )
    cell_style = ParagraphStyle(
        "ParkingReportCell",
        parent=body_style,
        fontSize=7,
        leading=9,
    )
    story = [
        Paragraph(escape(settings.PROJECT_NAME), body_style),
        Spacer(1, 3 * mm),
        Paragraph("Parking Session History", title_style),
        Paragraph(
            f"Date range: {escape(start_date)} to {escape(end_date)}"
            f" &nbsp;&nbsp; Generated: {escape(generated_at.isoformat(timespec='seconds'))}",
            body_style,
        ),
    ]
    filter_text = ", ".join(
        f"{escape(key.replace('_', ' ').title())}: {escape(value)}"
        for key, value in filters.items()
        if value
    ) or "None"
    story.extend(
        [
            Paragraph(f"Applied filters: {filter_text}", body_style),
            Paragraph(f"Records in this export: {len(rows)}", body_style),
            Spacer(1, 7 * mm),
        ]
    )

    headers = ("Parking ID", "Plate", "Category", "Slot", "Entry", "Exit", "Status", "Payment")
    table_data = [[Paragraph(escape(value), cell_style) for value in headers]]
    for row in rows:
        table_data.append(
            [
                Paragraph(escape(str(value if value is not None else "—")), cell_style)
                for value in (
                    row["record_id"],
                    row["plate"],
                    row["category"],
                    row["slot"],
                    row["entry_time"],
                    row["exit_time"],
                    row["status"],
                    row["payment_status"],
                )
            ]
        )
    table = Table(
        table_data,
        colWidths=(19 * mm, 43 * mm, 28 * mm, 18 * mm, 43 * mm, 43 * mm, 28 * mm, 29 * mm),
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), (colors.white, colors.HexColor("#F1F5F9"))),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    if not rows:
        story.append(Paragraph("No parking sessions matched these filters.", body_style))

    def draw_page(canvas, doc):
        canvas.saveState()
        page_width, _ = landscape(A4)
        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.line(14 * mm, 12 * mm, page_width - 14 * mm, 12 * mm)
        canvas.setFont(font_name, 8)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(14 * mm, 8 * mm, "Smart Parking · Confidential operational report")
        canvas.drawRightString(page_width - 14 * mm, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue()
