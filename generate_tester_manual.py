import os
import sys
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "FreshFold Laundry Marketplace — Field Tester Manual & QA Guide")
            self.drawRightString(612 - 54, 750, "CONFIDENTIAL / QA RUNBOOK")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 612 - 54, 744)
            
        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 612 - 54, 45)
        
        self.drawString(54, 32, f"Environment: Production Staging (Render + Neon Postgres) | Generated: {datetime.now().strftime('%b %d, %Y')}")
        self.drawRightString(612 - 54, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def build_manual_pdf(filename="FreshFold_Tester_Manual.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom palette
    PRIMARY = colors.HexColor("#0F172A")    # Deep Navy
    SECONDARY = colors.HexColor("#2563EB")  # Electric Blue
    ACCENT = colors.HexColor("#0D9488")     # Teal
    SUCCESS = colors.HexColor("#16A34A")    # Green
    WARNING = colors.HexColor("#D97706")    # Amber
    DANGER = colors.HexColor("#DC2626")     # Red
    LIGHT_BG = colors.HexColor("#F8FAFC")   # Slate 50
    CARD_BG = colors.HexColor("#F1F5F9")    # Slate 100
    BORDER = colors.HexColor("#E2E8F0")     # Slate 200
    TEXT_DARK = colors.HexColor("#1E293B")
    TEXT_MUTED = colors.HexColor("#64748B")

    # Typography styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=PRIMARY,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=SECONDARY,
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=SECONDARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=TEXT_DARK,
        spaceAfter=6
    )
    
    body_bold = ParagraphStyle(
        "BodyBoldCustom",
        parent=body_style,
        fontName="Helvetica-Bold"
    )

    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    code_style = ParagraphStyle(
        "CodeInline",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A")
    )
    
    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=TEXT_DARK
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell,
        fontName="Helvetica-Bold"
    )

    story = []

    # -------------------------------------------------------------
    # COVER / HEADER BANNER
    # -------------------------------------------------------------
    banner_data = [
        [
            Paragraph("<b>FRESHFOLD LAUNDRY MARKETPLACE</b>", ParagraphStyle("B1", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, textColor=SECONDARY)),
            Paragraph("<b>RELEASE VALIDATION MANUAL</b>", ParagraphStyle("B2", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=TEXT_MUTED, alignment=2))
        ],
        [
            Paragraph("Field Testing & End-to-End QA Runbook", title_style),
            Paragraph("<b>Target Version:</b> v1.2-prod<br/><b>Build:</b> Neon Postgres + Razorpay + Green API + Face++", ParagraphStyle("Meta", parent=table_cell, alignment=2, leading=12))
        ]
    ]
    banner_table = Table(banner_data, colWidths=[330, 174])
    banner_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(banner_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=SECONDARY, spaceBefore=6, spaceAfter=12))

    # Introduction Box
    summary_html = """<b>Instructions to Testers:</b> This manual is designed for quality assurance testers executing a real-world, live-environment simulation of the FreshFold laundry service workflow. You will simulate three roles: <b>Customer</b>, <b>Admin</b>, and <b>Laundry/Delivery Staff</b> across mobile and desktop devices. Follow each scenario sequentially and record observations in the sign-off matrix provided on the final page."""
    summary_table = Table([[Paragraph(summary_html, body_style)]], colWidths=[504])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CARD_BG),
        ('BOX', (0,0), (-1,-1), 1, BORDER),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # SECTION 1: SYSTEM ENVIRONMENT & CREDENTIALS
    # -------------------------------------------------------------
    story.append(Paragraph("1. System Environment & Access Credentials", h1_style))
    story.append(Paragraph("The system is deployed on Render backed by Neon Serverless PostgreSQL. Ensure you have network connectivity and an active WhatsApp number before starting.", body_style))

    cred_data = [
        [Paragraph("Role", table_header), Paragraph("Login URL", table_header), Paragraph("Identifier (Phone)", table_header), Paragraph("Password", table_header), Paragraph("Permissions / Focus", table_header)],
        [
            Paragraph("<b>Admin</b>", table_cell_bold),
            Paragraph("<code>/auth/login</code>", table_cell),
            Paragraph("<b>9999900001</b>", table_cell),
            Paragraph("<code>admin123</code>", table_cell),
            Paragraph("Approve KYC, configure pricing, create slots, staff management, order price overrides.", table_cell)
        ],
        [
            Paragraph("<b>Staff</b>", table_cell_bold),
            Paragraph("<code>/auth/login</code>", table_cell),
            Paragraph("<b>9999900002</b>", table_cell),
            Paragraph("<code>staff123</code>", table_cell),
            Paragraph("Pickup management, item intake verification, order status progression, OTP delivery verification.", table_cell)
        ],
        [
            Paragraph("<b>Customer</b>", table_cell_bold),
            Paragraph("<code>/auth/signup</code>", table_cell),
            Paragraph("<i>Your 10-digit Mobile</i>", table_cell),
            Paragraph("<i>Tester Choice</i>", table_cell),
            Paragraph("ID verification upload, slot booking, item service bundling, Razorpay online payment, tracking.", table_cell)
        ],
    ]
    cred_table = Table(cred_data, colWidths=[65, 85, 95, 75, 184])
    cred_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, CARD_BG])
    ]))
    story.append(cred_table)
    story.append(Spacer(1, 10))

    # Live Endpoint box
    endpoint_html = """<b>Primary Live Application URL:</b> <font color="#2563EB"><u>https://laundry-marketplace-1.onrender.com</u></font><br/>
    <b>Prerequisites:</b> 1x Smartphone (WhatsApp active), 1x Laptop/Desktop (recommended for dual-role testing in Incognito mode), 2 test images (ID card photo & clear portrait selfie)."""
    end_table = Table([[Paragraph(endpoint_html, body_style)]], colWidths=[504])
    end_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BFDBFE")),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(end_table)
    story.append(Spacer(1, 12))

    # -------------------------------------------------------------
    # SECTION 2: END-TO-END WORKFLOW MATRIX
    # -------------------------------------------------------------
    story.append(Paragraph("2. Full Real-Time Testing Workflow (7 Phases)", h1_style))
    story.append(Paragraph("Execute these phases in strict sequential order to validate database constraints, payment webhooks, external AI face verification, and WhatsApp message queues.", body_style))

    phases = [
        ("Phase 1: Customer Signup & Face++ AI Verification", [
            ("1.1", "Navigate to <code>/auth/signup</code> on mobile or desktop browser.", "Registration form loads with fields: Name, Phone, Address, Password, ID Proof upload, Selfie upload."),
            ("1.2", "Enter real 10-digit WhatsApp number, fill details, attach ID photo and Selfie. Submit.", "Account created. User directed to pending approval dashboard. Flash notice confirms submission."),
            ("1.3", "Log in as Admin (<code>9999900001</code>) and open <b>Customers</b> (<code>/admin/customers</code>).", "Admin sees new customer. Face++ background thread returns match score (% badge: Green &ge;70%, Red &lt;70%)."),
            ("1.4", "Click <b>Approve KYC</b> button as Admin.", "Customer status turns 'VERIFIED'. Green API triggers automated WhatsApp notification to customer welcoming them.")
        ]),
        ("Phase 2: Service Catalog Pricing & Pickup Slot Scheduling", [
            ("2.1", "As Admin, navigate to <b>Pricing</b> (<code>/admin/services</code>).", "Displays 9 default services (Wash ₹30, Iron ₹20, Wash & Iron ₹45, Dry Clean ₹120, etc.)."),
            ("2.2", "Edit a service price inline (e.g. Wash to ₹35) and toggle an active state. Save.", "Price update persists instantly to Neon Postgres. Active/inactive badges update cleanly."),
            ("2.3", "Navigate to <b>Slots</b> (<code>/admin/slots</code>) and create a slot for today's date.", "Slot added with specified date, start/end time window, capacity, and pickup address.")
        ]),
        ("Phase 3: Order Booking & Multi-Service Item Bundling", [
            ("3.1", "Log in as Customer. Click <b>Book pickup</b> (<code>/customer/book</code>).", "Available pickup slots display with remaining capacity. Customer selects the slot created in Phase 2."),
            ("3.2", "In the created Order page, upload an item photo (e.g., Silk Shirt) and enter note.", "Item appears in order checklist."),
            ("3.3", "Select multiple services via checkboxes (e.g., Wash ₹35 + Iron ₹20). Click Add.", "Item saves with bundled services. Price snapshot freezes. Order running total auto-increments to ₹55."),
            ("3.4", "Add a second item (e.g., Woolen Jacket) with 'Dry Clean' (₹120).", "Cumulative total dynamically updates to ₹175. Items display service tags and individual subtotals.")
        ]),
        ("Phase 4: Admin Intake Inspection & Approval", [
            ("4.1", "As Admin, open <b>Orders</b> &rarr; Click the pending order.", "Order detail shows uploaded item photos, customer selected services, and auto-computed total (₹175)."),
            ("4.2", "Inspect bag items. Optionally adjust amount via <b>Override Total Amount</b>.", "Admin can lock custom final price or leave auto-calculated total."),
            ("4.3", "Assign staff member (or leave unassigned) and click <b>Approve Pickup</b>.", "Status advances to 'PICKUP_APPROVED'. Green API sends automated WhatsApp pickup confirmation to customer.")
        ]),
        ("Phase 5: Online Payment Gateway (Razorpay)", [
            ("5.1", "As Customer, open the approved order. Review itemized bill. Click <b>Pay Now</b>.", "Razorpay modal pops up showing exact order total (₹175) and FreshFold branding."),
            ("5.2", "Select <b>Card</b> &rarr; Enter Razorpay test card: <code>4111 1111 1111 1111</code>, expiry <code>12/28</code>, CVV <code>123</code>.", "Simulated bank OTP page appears. Click <b>Success</b>."),
            ("5.3", "Verify post-payment redirection and state change.", "Payment verified via HMAC-SHA256 signature. Order status reflects 'Paid' (Badge: Green)."),
            ("5.4", "Click <b>Download Invoice (PDF)</b>.", "ReportLab PDF downloads instantly with complete breakdown, customer address, payment ID, and GST/PAN placeholder.")
        ]),
        ("Phase 6: Laundry Item Verification & Status Processing", [
            ("6.1", "Log in as Staff (<code>9999900002</code>). View <b>My Queue</b> (<code>/staff/</code>).", "Order appears in queue under 'PICKUP_APPROVED'."),
            ("6.2", "Staff clicks <b>Pickup Bag</b> &rarr; advances to 'PICKED_UP' &rarr; 'AT_LAUNDRY'.", "Audit trail logs timestamp and staff ID in <code>OrderStatusLog</code>."),
            ("6.3", "At laundry station, staff verifies each garment against uploaded photo checkboxes.", "Safety gate: 'Advance to Processing' remains locked until 100% of items are physically checked off."),
            ("6.4", "Advance order to 'PROCESSING', then to 'READY_FOR_DELIVERY'.", "Visual progress bar advances on both customer and admin dashboards.")
        ]),
        ("Phase 7: Delivery OTP Verification & WhatsApp PDF Dispatch", [
            ("7.1", "Staff advances order to <b>Out for Delivery</b>.", "Cryptographic 4-digit OTP generated. Green API dispatches WhatsApp alert to customer with the Delivery OTP."),
            ("7.2", "Staff arrives at customer destination and opens order delivery confirmation form.", "Input field for Customer Delivery OTP displays with rate-limiting notice."),
            ("7.3", "<b>Negative Test:</b> Enter wrong OTP (e.g., <code>0000</code>).", "Error flash: 'That code does not match'. Failed attempt counter increments (lockout at 5 attempts)."),
            ("7.4", "<b>Positive Test:</b> Enter the actual OTP from customer WhatsApp.", "Order marked 'DELIVERED'. Status closes. Audit log commits."),
            ("7.5", "Check Customer WhatsApp inbox.", "Green API delivers automated 'Thank You' text + attaches the final ReportLab PDF invoice document directly into WhatsApp.")
        ]),
    ]

    for p_title, p_steps in phases:
        story.append(Paragraph(p_title, h2_style))
        step_data = [[Paragraph("Step", table_header), Paragraph("Action / Procedure", table_header), Paragraph("Expected System Outcome", table_header)]]
        for sid, action, exp in p_steps:
            step_data.append([
                Paragraph(f"<b>{sid}</b>", table_cell_bold),
                Paragraph(action, table_cell),
                Paragraph(exp, table_cell)
            ])
        t = Table(step_data, colWidths=[35, 235, 234])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), PRIMARY),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, CARD_BG])
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    # Page break before checklist & edge cases
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SECTION 3: EDGE CASES & NEGATIVE TESTING RUNBOOK
    # -------------------------------------------------------------
    story.append(Paragraph("3. Edge Cases & Resilience Testing Matrix", h1_style))
    story.append(Paragraph("Testers must deliberately attempt the following boundary conditions to verify error handling and security controls:", body_style))

    edge_data = [
        [Paragraph("Ref #", table_header), Paragraph("Category", table_header), Paragraph("Test Scenario", table_header), Paragraph("Expected Defensive Handling", table_header)],
        [
            Paragraph("SEC-01", table_cell_bold),
            Paragraph("Security & RBAC", table_cell),
            Paragraph("Logged-in Customer attempts to browse <code>/admin/dashboard</code> or <code>/staff/</code>.", table_cell),
            Paragraph("HTTP 403 Forbidden or redirection to customer dashboard with error notice.", table_cell)
        ],
        [
            Paragraph("SEC-02", table_cell_bold),
            Paragraph("Media Privacy", table_cell),
            Paragraph("Copy photo URL of another user's ID/Selfie and open in incognito window.", table_cell),
            Paragraph("HTTP 403 / 401. Files are served via protected view functions, never exposed statically.", table_cell)
        ],
        [
            Paragraph("MOB-01", table_cell_bold),
            Paragraph("Mobile UX", table_cell),
            Paragraph("Load <code>/customer/order_detail</code> on 360px viewport (iOS Safari / Android Chrome).", table_cell),
            Paragraph("Checkboxes remain tap-friendly (&gt;44px targets), tables stack using data-labels, Pay Now modal fits.", table_cell)
        ],
        [
            Paragraph("PAY-01", table_cell_bold),
            Paragraph("Payment Safety", table_cell),
            Paragraph("Cancel or close Razorpay payment modal halfway through transaction.", table_cell),
            Paragraph("Order remains 'PICKUP_APPROVED' with payment status 'Pending'. No phantom billing recorded.", table_cell)
        ],
        [
            Paragraph("OTP-01", table_cell_bold),
            Paragraph("Brute Force Limit", table_cell),
            Paragraph("Submit incorrect delivery OTP 5 consecutive times on <code>/staff/confirm-delivery</code>.", table_cell),
            Paragraph("Account throttled. Order flags security lockout requiring admin intervention.", table_cell)
        ],
        [
            Paragraph("NET-01", table_cell_bold),
            Paragraph("Third-Party API", table_cell),
            Paragraph("Simulate Face++ or Green API timeout/bad credentials.", table_cell),
            Paragraph("App does NOT crash. KYC falls back to 'PENDING' for manual review; WhatsApp logs warning.", table_cell)
        ],
    ]
    edge_table = Table(edge_data, colWidths=[45, 80, 185, 194])
    edge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, CARD_BG])
    ]))
    story.append(edge_table)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------
    # SECTION 4: TEST EXECUTION LOG & SIGN-OFF SHEET
    # -------------------------------------------------------------
    story.append(Paragraph("4. Tester Field Log & Formal Sign-Off Sheet", h1_style))
    story.append(Paragraph("Each tester must complete this verification log upon conclusion of the end-to-end testing cycle.", body_style))

    sign_data = [
        [Paragraph("Test Phase", table_header), Paragraph("Target Functionality", table_header), Paragraph("Pass / Fail", table_header), Paragraph("Tester Initials & Notes", table_header)],
        [Paragraph("Phase 1", table_cell_bold), Paragraph("Customer Signup & Face++ AI Match / Admin Approval", table_cell), Paragraph("[  ] Pass<br/>[  ] Fail", table_cell), Paragraph("", table_cell)],
        [Paragraph("Phase 2", table_cell_bold), Paragraph("Service Catalog Pricing CRUD & Slot Creation", table_cell), Paragraph("[  ] Pass<br/>[  ] Fail", table_cell), Paragraph("", table_cell)],
        [Paragraph("Phase 3", table_cell_bold), Paragraph("Slot Booking & Multi-Service Item Bundling", table_cell), Paragraph("[  ] Pass<br/>[  ] Fail", table_cell), Paragraph("", table_cell)],
        [Paragraph("Phase 4", table_cell_bold), Paragraph("Admin Bag Check, Price Override & WhatsApp Pickup Alert", table_cell), Paragraph("[  ] Pass<br/>[  ] Fail", table_cell), Paragraph("", table_cell)],
        [Paragraph("Phase 5", table_cell_bold), Paragraph("Razorpay Online Checkout & PDF Invoice Download", table_cell), Paragraph("[  ] Pass<br/>[  ] Fail", table_cell), Paragraph("", table_cell)],
        [Paragraph("Phase 6", table_cell_bold), Paragraph("Laundry Physical Checkbox Gate & Status Progression", table_cell), Paragraph("[  ] Pass<br/>[  ] Fail", table_cell), Paragraph("", table_cell)],
        [Paragraph("Phase 7", table_cell_bold), Paragraph("Delivery OTP Verification & WhatsApp PDF Dispatch", table_cell), Paragraph("[  ] Pass<br/>[  ] Fail", table_cell), Paragraph("", table_cell)],
        [Paragraph("Edge Cases", table_cell_bold), Paragraph("Mobile Responsiveness, Brute-Force & Access Guards", table_cell), Paragraph("[  ] Pass<br/>[  ] Fail", table_cell), Paragraph("", table_cell)],
    ]
    sign_table = Table(sign_data, colWidths=[70, 210, 70, 154])
    sign_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, CARD_BG])
    ]))
    story.append(sign_table)
    story.append(Spacer(1, 14))

    # Signature Block
    sig_block = [
        [
            Paragraph("<b>Primary Tester Name:</b> ___________________________", body_style),
            Paragraph("<b>Testing Device / OS:</b> ___________________________", body_style)
        ],
        [
            Paragraph("<b>Tester WhatsApp #:</b> ___________________________", body_style),
            Paragraph("<b>Execution Date:</b> ___________________________", body_style)
        ],
        [
            Paragraph("<b>Final Sign-Off:</b> [  ] READY FOR PRODUCTION   [  ] DEFECTS BLOCKING", body_bold),
            Paragraph("<b>Signature:</b> ___________________________", body_style)
        ]
    ]
    sig_table = Table(sig_block, colWidths=[252, 252])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(sig_table)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Manual successfully built at {filename}")

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "FreshFold_Tester_Manual.pdf"
    build_manual_pdf(out_file)
