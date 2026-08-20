from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, PickupSlot, Order, CANCELLED, notify_user, notify_role
from app.utils import role_required

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@admin_bp.before_request
@login_required
@role_required("admin")
def _guard():
    pass


@admin_bp.route("/")
def dashboard():
    pending_customers = User.query.filter_by(role="customer", verification_status="PENDING").count()
    pending_pickups = Order.query.filter_by(status="PENDING_PICKUP_APPROVAL").count()
    active_orders = Order.query.filter(
        Order.status.notin_(["DELIVERED", CANCELLED])
    ).count()
    return render_template(
        "admin/dashboard.html",
        pending_customers=pending_customers,
        pending_pickups=pending_pickups,
        active_orders=active_orders,
    )


# ---------------------------------------------------------------------------
# Customer KYC approval
# ---------------------------------------------------------------------------

@admin_bp.route("/customers")
def customers():
    status = request.args.get("status", "PENDING")
    q = User.query.filter_by(role="customer")
    if status != "ALL":
        q = q.filter_by(verification_status=status)
    customers = q.order_by(User.created_at.desc()).all()
    return render_template("admin/customers.html", customers=customers, status=status)


@admin_bp.route("/customers/<int:user_id>/approve", methods=["POST"])
def approve_customer(user_id):
    user = User.query.get_or_404(user_id)
    user.verification_status = "APPROVED"
    user.rejection_reason = None
    notify_user(user, "Your ID was approved — you can now book a pickup.", link="/customer/book")
    db.session.commit()
    flash(f"{user.name} approved.", "success")
    return redirect(url_for("admin.customers"))


@admin_bp.route("/customers/<int:user_id>/reject", methods=["POST"])
def reject_customer(user_id):
    user = User.query.get_or_404(user_id)
    reason = request.form.get("reason", "").strip()
    user.verification_status = "REJECTED"
    user.rejection_reason = reason or "ID proof could not be verified."
    notify_user(user, "Your ID verification was rejected — see your dashboard for details.", link="/customer/dashboard")
    db.session.commit()
    flash(f"{user.name} rejected.", "success")
    return redirect(url_for("admin.customers"))


# ---------------------------------------------------------------------------
# Pickup slots
# ---------------------------------------------------------------------------

@admin_bp.route("/slots", methods=["GET", "POST"])
def slots():
    if request.method == "POST":
        try:
            slot = PickupSlot(
                date=datetime.strptime(request.form["date"], "%Y-%m-%d").date(),
                start_time=datetime.strptime(request.form["start_time"], "%H:%M").time(),
                end_time=datetime.strptime(request.form["end_time"], "%H:%M").time(),
                location=request.form["location"].strip(),
                capacity=int(request.form.get("capacity") or 5),
                created_by=current_user.id,
            )
        except (ValueError, KeyError):
            flash("Please fill in the slot details correctly.", "error")
            return redirect(url_for("admin.slots"))
        db.session.add(slot)
        db.session.commit()
        flash("Pickup slot added.", "success")
        return redirect(url_for("admin.slots"))

    all_slots = PickupSlot.query.order_by(PickupSlot.date, PickupSlot.start_time).all()
    return render_template("admin/slots.html", slots=all_slots)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@admin_bp.route("/orders")
def orders():
    status = request.args.get("status", "PENDING_PICKUP_APPROVAL")
    q = Order.query
    if status != "ALL":
        q = q.filter_by(status=status)
    order_list = q.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=order_list, status=status)


@admin_bp.route("/orders/<int:order_id>")
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    staff = User.query.filter_by(role="staff").all()
    return render_template("admin/order_detail.html", order=order, staff=staff)


@admin_bp.route("/orders/<int:order_id>/approve-pickup", methods=["POST"])
def approve_pickup(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status != "PENDING_PICKUP_APPROVAL":
        abort(400)
    staff_id = request.form.get("staff_id")
    if staff_id:
        order.assigned_staff_id = int(staff_id)
    order.advance_to("PICKUP_APPROVED", current_user, note="Bag contents matched uploaded items — pickup approved")
    if order.assigned_staff_id:
        staff = User.query.get(order.assigned_staff_id)
        notify_user(staff, f"Order #{order.id} approved for pickup — assigned to you", link=f"/staff/order/{order.id}")
    else:
        notify_role("staff", f"Order #{order.id} approved for pickup — unassigned", link=f"/staff/order/{order.id}")
    db.session.commit()
    flash("Pickup approved.", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))


@admin_bp.route("/orders/<int:order_id>/send-back", methods=["POST"])
def send_back(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status != "PENDING_PICKUP_APPROVAL":
        abort(400)
    reason = request.form.get("reason", "").strip() or "Items didn't match — please re-check and resubmit."
    order.advance_to("AWAITING_ITEMS", current_user, note=reason)
    db.session.commit()
    flash("Sent back to the customer for correction.", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))


@admin_bp.route("/orders/<int:order_id>/assign", methods=["POST"])
def assign_staff(order_id):
    order = Order.query.get_or_404(order_id)
    staff_id = request.form.get("staff_id")
    order.assigned_staff_id = int(staff_id) if staff_id else None
    if order.assigned_staff_id:
        staff = User.query.get(order.assigned_staff_id)
        notify_user(staff, f"Order #{order.id} assigned to you", link=f"/staff/order/{order.id}")
    db.session.commit()
    flash("Staff assignment updated.", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))


# ---------------------------------------------------------------------------
# Staff accounts
# ---------------------------------------------------------------------------

@admin_bp.route("/staff", methods=["GET", "POST"])
def manage_staff():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not name or not phone or not password:
            flash("Name, phone, and password are all required.", "error")
            return redirect(url_for("admin.manage_staff"))
        if len(password) < 6:
            flash("Password should be at least 6 characters.", "error")
            return redirect(url_for("admin.manage_staff"))
        if User.query.filter_by(phone=phone).first():
            flash("A user with this phone number already exists.", "error")
            return redirect(url_for("admin.manage_staff"))

        staff = User(role="staff", name=name, phone=phone)
        staff.set_password(password)
        db.session.add(staff)
        db.session.commit()
        flash(f"Staff account created for {name}. Share their phone number and password with them directly.", "success")
        return redirect(url_for("admin.manage_staff"))

    staff_list = User.query.filter_by(role="staff").order_by(User.created_at.desc()).all()
    return render_template("admin/staff.html", staff_list=staff_list)
