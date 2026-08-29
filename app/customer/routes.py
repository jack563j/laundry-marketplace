from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import PickupSlot, Order, OrderItem, OrderItemService, ServiceType, notify_role
from app.utils import role_required, save_upload

customer_bp = Blueprint("customer", __name__, template_folder="../templates/customer")


@customer_bp.before_request
@login_required
@role_required("customer")
def _guard():
    pass


@customer_bp.route("/dashboard")
def dashboard():
    orders = (
        Order.query.filter_by(customer_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("customer/dashboard.html", orders=orders)


@customer_bp.route("/book", methods=["GET", "POST"])
def book():
    if not current_user.is_verified_customer:
        flash("Your ID proof is still under review. You'll be able to book once approved.", "error")
        return redirect(url_for("customer.dashboard"))

    slots = (
        PickupSlot.query.filter(PickupSlot.date >= date.today())
        .order_by(PickupSlot.date, PickupSlot.start_time)
        .all()
    )
    open_slots = [s for s in slots if not s.is_full]

    if request.method == "POST":
        slot_id = request.form.get("slot_id")
        notes = request.form.get("special_notes", "").strip()
        slot = PickupSlot.query.get(slot_id)
        if not slot or slot.is_full:
            flash("That slot is no longer available. Pick another one.", "error")
            return render_template("customer/book.html", slots=open_slots)

        order = Order(customer_id=current_user.id, pickup_slot_id=slot.id, special_notes=notes)
        order.advance_to("AWAITING_ITEMS", current_user, note="Order created")
        db.session.add(order)
        db.session.commit()
        flash("Slot booked! Now add photos of each item so we know what's in the bag.", "success")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    return render_template("customer/book.html", slots=open_slots)


@customer_bp.route("/order/<int:order_id>")
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        abort(403)
    active_services = ServiceType.query.filter_by(is_active=True).order_by(ServiceType.name).all()
    razorpay_key = current_app.config.get("RAZORPAY_KEY_ID", "")
    return render_template(
        "customer/order_detail.html",
        order=order,
        active_services=active_services,
        razorpay_key=razorpay_key,
    )


@customer_bp.route("/order/<int:order_id>/add-item", methods=["POST"])
def add_item(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        abort(403)
    if order.status != "AWAITING_ITEMS":
        flash("This order has already been submitted for pickup.", "error")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    photo = request.files.get("photo")
    description = request.form.get("description", "").strip()
    instructions = request.form.get("instructions", "").strip()
    # Selected service IDs (multi-select checkboxes)
    service_ids = request.form.getlist("service_ids")

    if not photo or photo.filename == "":
        flash("Please attach a photo of the item.", "error")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    path = save_upload(photo, current_app.config["ITEM_PHOTO_FOLDER"], "items")
    if not path:
        flash("Photo must be a PNG/JPG/WEBP image.", "error")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    if not service_ids:
        flash("Please select at least one service for this item.", "error")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    item = OrderItem(
        order_id=order.id,
        photo_path=path,
        description=description,
        instructions=instructions,
    )
    db.session.add(item)
    db.session.flush()  # get item.id before adding services

    # Snapshot price at order time so admin price changes don't affect past orders
    for sid in service_ids:
        svc = ServiceType.query.get(int(sid))
        if svc and svc.is_active:
            db.session.add(OrderItemService(
                order_item_id=item.id,
                service_type_id=svc.id,
                price_snapshot=svc.price,
            ))

    db.session.commit()
    return redirect(url_for("customer.order_detail", order_id=order.id))


@customer_bp.route("/order/<int:order_id>/remove-item/<int:item_id>", methods=["POST"])
def remove_item(order_id, item_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        abort(403)
    if order.status != "AWAITING_ITEMS":
        abort(400)
    item = OrderItem.query.get_or_404(item_id)
    if item.order_id != order.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("customer.order_detail", order_id=order.id))


@customer_bp.route("/order/<int:order_id>/submit", methods=["POST"])
def submit_for_pickup(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        abort(403)
    if order.status != "AWAITING_ITEMS":
        abort(400)
    if len(order.items) == 0:
        flash("Add at least one item photo before submitting.", "error")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    order.advance_to("PENDING_PICKUP_APPROVAL", current_user, note="Customer submitted items for review", notify_customer=False)
    notify_role("admin", f"Order #{order.id} ready for pickup review ({current_user.name})", link=f"/admin/orders/{order.id}")
    db.session.commit()
    flash("Submitted! We'll confirm your pickup once the admin reviews your items.", "success")
    return redirect(url_for("customer.order_detail", order_id=order.id))


@customer_bp.route("/order/<int:order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        abort(403)
    if order.status in ("PICKED_UP", "AT_LAUNDRY", "WASHING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"):
        flash("This order can no longer be cancelled — it's already in progress.", "error")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    order.advance_to("CANCELLED", current_user, note="Cancelled by customer")
    db.session.commit()
    flash("Order cancelled.", "success")
    return redirect(url_for("customer.dashboard"))
