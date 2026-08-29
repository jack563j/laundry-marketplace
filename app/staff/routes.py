from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db, limiter
from app.models import Order, OrderItem, generate_otp
from app.utils import role_required

staff_bp = Blueprint("staff", __name__, template_folder="../templates/staff")

# What this role is allowed to move an order to, from a given status.
# OUT_FOR_DELIVERY -> DELIVERED is deliberately NOT here: that transition
# requires the customer's OTP and goes through confirm_delivery() instead.
NEXT_STATUS = {
    "PICKUP_APPROVED": "PICKED_UP",
    "PICKED_UP": "AT_LAUNDRY",
    "AT_LAUNDRY": "WASHING",
    "WASHING": "READY",
    "READY": "OUT_FOR_DELIVERY",
}
NEXT_LABEL = {
    "PICKED_UP": "Confirm picked up",
    "AT_LAUNDRY": "Confirm received at laundry",
    "WASHING": "Start washing",
    "READY": "Mark ready for delivery",
    "OUT_FOR_DELIVERY": "Start delivery",
}


@staff_bp.before_request
@login_required
@role_required("staff")
def _guard():
    pass


@staff_bp.route("/")
def dashboard():
    active = (
        Order.query.filter(
            Order.status.in_(list(NEXT_STATUS.keys()) + ["OUT_FOR_DELIVERY"])
        )
        .order_by(Order.created_at)
        .all()
    )
    return render_template("staff/dashboard.html", orders=active)


@staff_bp.route("/order/<int:order_id>")
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    next_status = NEXT_STATUS.get(order.status)
    next_label = NEXT_LABEL.get(next_status) if next_status else None
    # Item verification is required before an order can leave AT_LAUNDRY
    items_checked = all(i.checked_at_laundry for i in order.items) if order.items else True
    return render_template(
        "staff/order_detail.html",
        order=order,
        next_status=next_status,
        next_label=next_label,
        items_checked=items_checked,
    )


@staff_bp.route("/order/<int:order_id>/toggle-item/<int:item_id>", methods=["POST"])
def toggle_item(order_id, item_id):
    item = OrderItem.query.get_or_404(item_id)
    if item.order_id != order_id:
        abort(403)
    item.checked_at_laundry = not item.checked_at_laundry
    db.session.commit()
    return redirect(url_for("staff.order_detail", order_id=order_id))


@staff_bp.route("/order/<int:order_id>/advance", methods=["POST"])
def advance(order_id):
    order = Order.query.get_or_404(order_id)
    next_status = NEXT_STATUS.get(order.status)
    if not next_status:
        abort(400)

    if order.status == "AT_LAUNDRY" and not all(i.checked_at_laundry for i in order.items):
        flash("Check off every item against the photos before moving this order on — that's what stops mix-ups.", "error")
        return redirect(url_for("staff.order_detail", order_id=order.id))

    order.advance_to(next_status, current_user, note=NEXT_LABEL.get(next_status))
    if order.assigned_staff_id is None:
        order.assigned_staff_id = current_user.id

    # Generate the delivery OTP the moment the order heads out — it's shown
    # to the customer in-app and never sent anywhere staff can see it here.
    if next_status == "OUT_FOR_DELIVERY":
        order.delivery_otp = generate_otp()
        order.otp_attempts = 0
        db.session.commit()
        # WhatsApp OTP to customer
        from app.services.whatsapp_service import notify_out_for_delivery
        notify_out_for_delivery(order.customer, order)
    else:
        db.session.commit()

    flash("Order updated.", "success")
    return redirect(url_for("staff.order_detail", order_id=order.id))


@staff_bp.route("/order/<int:order_id>/confirm-delivery", methods=["POST"])
@limiter.limit("10 per minute")
def confirm_delivery(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status != "OUT_FOR_DELIVERY":
        abort(400)

    if order.otp_attempts >= 5:
        flash("Too many incorrect attempts. Ask the customer to check the app, or contact the admin.", "error")
        return redirect(url_for("staff.order_detail", order_id=order.id))

    entered = request.form.get("otp", "").strip()
    if entered and entered == order.delivery_otp:
        order.advance_to("DELIVERED", current_user, note="Delivery confirmed by customer OTP")
        db.session.commit()
        flash("Delivery confirmed.", "success")
        # Send invoice PDF via WhatsApp
        try:
            from app.services.pdf_service import generate_invoice_pdf
            from app.services.whatsapp_service import notify_delivered_with_invoice
            pdf_bytes = generate_invoice_pdf(order)
            notify_delivered_with_invoice(order.customer, order, pdf_bytes)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("WhatsApp invoice send failed: %s", exc)
    else:
        order.otp_attempts = (order.otp_attempts or 0) + 1
        db.session.commit()
        flash("That code doesn't match. Ask the customer to read it from their app again.", "error")

    return redirect(url_for("staff.order_detail", order_id=order.id))
