import hashlib
import hmac
import logging

from flask import (
    Blueprint, abort, current_app, jsonify, redirect,
    render_template, request, send_file, url_for, flash, Response
)
from flask_login import login_required, current_user
import io

from app.extensions import db
from app.models import Order, Payment, CANCELLED
from app.services.pdf_service import generate_invoice_pdf
from app.services.whatsapp_service import notify_delivered_with_invoice

logger = logging.getLogger(__name__)

payment_bp = Blueprint("payment", __name__)


def _razorpay_client():
    key_id = current_app.config.get("RAZORPAY_KEY_ID", "")
    key_secret = current_app.config.get("RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        return None
    try:
        import razorpay  # lazy import — not available until pip install on Render
        return razorpay.Client(auth=(key_id, key_secret))
    except ImportError:
        logger.error("razorpay package not installed")
        return None


def _get_order_for_payment(order_id):
    """Fetch order and enforce ownership (customer) or admin/staff access."""
    order = Order.query.get_or_404(order_id)
    if current_user.role == "customer" and order.customer_id != current_user.id:
        abort(403)
    return order


# ---------------------------------------------------------------------------
# Step 1 — Create Razorpay order
# ---------------------------------------------------------------------------
@payment_bp.route("/order/<int:order_id>/create", methods=["POST"])
@login_required
def create_payment(order_id):
    order = _get_order_for_payment(order_id)

    if order.payment_status == "PAID":
        return jsonify({"error": "Order is already paid."}), 400

    amount_inr = order.total_amount if order.total_amount is not None else order.computed_total
    if amount_inr <= 0:
        return jsonify({"error": "Order amount is zero — nothing to pay."}), 400

    client = _razorpay_client()
    if not client:
        return jsonify({"error": "Payment gateway not configured. Contact admin."}), 503

    try:
        rz_order = client.order.create({
            "amount": int(amount_inr * 100),   # Razorpay uses paise
            "currency": "INR",
            "receipt": f"FF-{order.id}",
            "payment_capture": 1,
        })
    except Exception as exc:
        logger.error("Razorpay order creation failed: %s", exc)
        return jsonify({"error": "Could not create payment order. Try again."}), 500

    # Save a Payment record so we can reconcile later
    payment = Payment(
        order_id=order.id,
        razorpay_order_id=rz_order["id"],
        amount=amount_inr,
        status="CREATED",
    )
    db.session.add(payment)
    db.session.commit()

    return jsonify({
        "razorpay_order_id": rz_order["id"],
        "amount": int(amount_inr * 100),
        "currency": "INR",
        "key_id": current_app.config["RAZORPAY_KEY_ID"],
        "order_id": order.id,
        "customer_name": order.customer.name,
        "customer_phone": order.customer.phone,
        "customer_email": order.customer.email or "",
    })


# ---------------------------------------------------------------------------
# Step 2 — Verify payment signature and mark order paid
# ---------------------------------------------------------------------------
@payment_bp.route("/order/<int:order_id>/verify", methods=["POST"])
@login_required
def verify_payment(order_id):
    order = _get_order_for_payment(order_id)

    rz_order_id = request.form.get("razorpay_order_id", "")
    rz_payment_id = request.form.get("razorpay_payment_id", "")
    rz_signature = request.form.get("razorpay_signature", "")

    key_secret = current_app.config.get("RAZORPAY_KEY_SECRET", "").encode()
    expected = hmac.new(
        key_secret,
        f"{rz_order_id}|{rz_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, rz_signature):
        flash("Payment verification failed — signature mismatch. Contact support.", "error")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    # Update Payment record
    payment = Payment.query.filter_by(
        order_id=order.id, razorpay_order_id=rz_order_id
    ).first()
    if payment:
        payment.razorpay_payment_id = rz_payment_id
        payment.status = "SUCCESS"

    # Mark order paid
    order.payment_status = "PAID"
    order.payment_id = rz_payment_id
    db.session.commit()

    # Send WhatsApp invoice if order is already delivered
    if order.status == "DELIVERED":
        try:
            pdf_bytes = generate_invoice_pdf(order)
            notify_delivered_with_invoice(order.customer, order, pdf_bytes)
        except Exception as exc:
            logger.error("Failed to send WhatsApp invoice after payment: %s", exc)

    flash("Payment successful! ✅ Your invoice is ready to download.", "success")
    return redirect(url_for("customer.order_detail", order_id=order.id))


# ---------------------------------------------------------------------------
# Invoice download — PDF
# ---------------------------------------------------------------------------
@payment_bp.route("/order/<int:order_id>/invoice")
@login_required
def download_invoice(order_id):
    order = _get_order_for_payment(order_id)

    # Allow download once paid OR if admin/staff
    if current_user.role == "customer" and order.payment_status not in ("PAID", "WAIVED"):
        flash("Invoice is available after payment is completed.", "error")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    try:
        pdf_bytes = generate_invoice_pdf(order)
    except Exception as exc:
        logger.error("Invoice generation failed for order %d: %s", order_id, exc)
        flash("Could not generate invoice. Please try again.", "error")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=FreshFold_Invoice_Order{order.id}.pdf"
        },
    )
