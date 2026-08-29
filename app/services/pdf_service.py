"""
PDF Invoice generator using ReportLab (pure Python, no system deps).

Generates a professional A4 invoice PDF for a delivered order,
including: FreshFold branding, customer details, itemised service
breakdown, payment summary, and order timeline.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

# Brand colours
BRAND_BLUE = colors.HexColor("#1a56db")
BRAND_LIGHT = colors.HexColor("#eff6ff")
DARK_TEXT = colors.HexColor("#111827")
GREY_TEXT = colors.HexColor("#6b7280")
SUCCESS_GREEN = colors.HexColor("#059669")


def generate_invoice_pdf(order) -> bytes:
    """
    Generate a PDF invoice for the given Order object.
    Returns the raw PDF bytes.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    story = []

    # -----------------------------------------------------------------------
    # Header — Brand + Invoice title
    # -----------------------------------------------------------------------
    header_style = ParagraphStyle(
        "header", fontSize=26, fontName="Helvetica-Bold",
        textColor=BRAND_BLUE, alignment=TA_LEFT,
    )
    sub_style = ParagraphStyle(
        "sub", fontSize=10, fontName="Helvetica",
        textColor=GREY_TEXT, alignment=TA_LEFT,
    )
    invoice_style = ParagraphStyle(
        "invoice_title", fontSize=14, fontName="Helvetica-Bold",
        textColor=DARK_TEXT, alignment=TA_RIGHT,
    )
    meta_style = ParagraphStyle(
        "meta", fontSize=9, fontName="Helvetica",
        textColor=GREY_TEXT, alignment=TA_RIGHT,
    )

    header_data = [
        [
            Paragraph("🧺 FreshFold", header_style),
            Paragraph("INVOICE", invoice_style),
        ],
        [
            Paragraph("Your trusted laundry partner", sub_style),
            Paragraph(
                f"Invoice #FF-{order.id:05d}<br/>"
                f"Date: {datetime.utcnow().strftime('%d %b %Y')}<br/>"
                f"Order: #{order.id}",
                meta_style,
            ),
        ],
    ]
    header_table = Table(header_data, colWidths=[90 * mm, 80 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=8))

    # -----------------------------------------------------------------------
    # Bill To — customer info
    # -----------------------------------------------------------------------
    section_title_style = ParagraphStyle(
        "section_title", fontSize=9, fontName="Helvetica-Bold",
        textColor=GREY_TEXT, spaceBefore=6, spaceAfter=2,
    )
    value_style = ParagraphStyle(
        "value", fontSize=10, fontName="Helvetica", textColor=DARK_TEXT,
    )
    small_style = ParagraphStyle(
        "small", fontSize=9, fontName="Helvetica", textColor=GREY_TEXT,
    )

    customer = order.customer
    slot = order.pickup_slot

    bill_to_data = [
        [
            _section_block("BILL TO", [
                f"<b>{customer.name}</b>",
                f"📱 {customer.phone}",
                customer.address or "",
            ]),
            _section_block("PICKUP SLOT", [
                f"📅 {slot.date.strftime('%d %b %Y')}",
                f"🕐 {slot.start_time.strftime('%I:%M %p')} – {slot.end_time.strftime('%I:%M %p')}",
                f"📍 {slot.location}",
            ]),
            _section_block("PAYMENT STATUS", [
                f"<font color='{'#059669' if order.payment_status == 'PAID' else '#dc2626'}'>"
                f"<b>{'✅ PAID' if order.payment_status == 'PAID' else '⏳ UNPAID'}</b></font>",
                f"Method: Razorpay" if order.payment_id else "Method: —",
                f"Ref: {order.payment_id or '—'}",
            ]),
        ]
    ]
    bill_table = Table(bill_to_data, colWidths=[60 * mm, 65 * mm, 55 * mm])
    bill_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(bill_table)
    story.append(Spacer(1, 8 * mm))

    # -----------------------------------------------------------------------
    # Items + Services table
    # -----------------------------------------------------------------------
    story.append(Paragraph("ITEMS & SERVICES", section_title_style))
    story.append(Spacer(1, 2 * mm))

    table_data = [["#", "Item Description", "Services", "Qty", "Amount"]]

    for idx, item in enumerate(order.items, 1):
        service_names = "\n".join(s.service_type.name for s in item.services) or "—"
        table_data.append([
            str(idx),
            item.description or f"Item {idx}",
            service_names,
            "1",
            f"₹{item.item_total:.2f}",
        ])

    items_table = Table(
        table_data,
        colWidths=[10 * mm, 50 * mm, 60 * mm, 12 * mm, 28 * mm],
    )
    items_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        # Data rows
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    # -----------------------------------------------------------------------
    # Totals block
    # -----------------------------------------------------------------------
    computed = order.computed_total
    final_total = order.total_amount if order.total_amount is not None else computed

    totals_data = []
    if order.total_amount is not None and abs(order.total_amount - computed) > 0.01:
        totals_data.append(["Subtotal (computed):", f"₹{computed:.2f}"])
        totals_data.append(["Adjustment:", f"₹{order.total_amount - computed:+.2f}"])
    totals_data.append(["", ""])  # spacer row
    totals_data.append(["TOTAL AMOUNT:", f"₹{final_total:.2f}"])

    totals_table = Table(totals_data, colWidths=[130 * mm, 30 * mm])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -2), 9),
        ("TEXTCOLOR", (0, 0), (-1, -2), GREY_TEXT),
        # Grand total row
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("TEXTCOLOR", (0, -1), (-1, -1), DARK_TEXT),
        ("LINEABOVE", (0, -1), (-1, -1), 1, DARK_TEXT),
        ("TOPPADDING", (0, -1), (-1, -1), 4),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 6 * mm))

    # -----------------------------------------------------------------------
    # Order timeline (condensed)
    # -----------------------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e5e7eb"), spaceAfter=4))
    story.append(Paragraph("ORDER TIMELINE", section_title_style))

    timeline_data = [["Status", "Date & Time", "Note"]]
    for log in order.logs:
        from app.models import ORDER_STATUS_LABELS
        label = ORDER_STATUS_LABELS.get(log.status, log.status)
        timeline_data.append([
            label,
            log.timestamp.strftime("%d %b %Y, %I:%M %p"),
            log.note or "—",
        ])

    timeline_table = Table(timeline_data, colWidths=[55 * mm, 50 * mm, 65 * mm])
    timeline_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (0, 1), (-1, -1), GREY_TEXT),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(timeline_table)
    story.append(Spacer(1, 8 * mm))

    # -----------------------------------------------------------------------
    # Footer
    # -----------------------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_BLUE, spaceAfter=4))
    footer_style = ParagraphStyle(
        "footer", fontSize=8, fontName="Helvetica",
        textColor=GREY_TEXT, alignment=TA_CENTER,
    )
    story.append(Paragraph(
        "Thank you for choosing FreshFold! 🧺  |  This is a computer-generated invoice.",
        footer_style,
    ))

    doc.build(story)
    return buffer.getvalue()


def _section_block(title: str, lines: list) -> Paragraph:
    """Helper: renders a labelled block of text for the bill-to section."""
    style = ParagraphStyle(
        "block", fontSize=9, fontName="Helvetica", textColor=colors.HexColor("#111827"),
        leading=14,
    )
    label_style = ParagraphStyle(
        "label", fontSize=8, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#6b7280"), spaceBefore=0, spaceAfter=2,
    )
    from reportlab.platypus import KeepTogether
    content = f"<font size='8' color='#6b7280'><b>{title}</b></font><br/>" + "<br/>".join(lines)
    return Paragraph(content, style)
