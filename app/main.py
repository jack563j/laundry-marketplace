from flask import Blueprint, redirect, url_for, send_from_directory, current_app, abort, render_template
from flask_login import current_user, login_required

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role == "customer":
        return redirect(url_for("customer.dashboard"))
    if current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))
    if current_user.role == "staff":
        return redirect(url_for("staff.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/notifications")
@login_required
def notifications():
    from app.extensions import db
    from app.models import Notification

    items = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    unread = [n for n in items if not n.is_read]
    for n in unread:
        n.is_read = True
    if unread:
        db.session.commit()
    return render_template("notifications.html", items=items)


# ---------------------------------------------------------------------------
# Protected file serving.
#
# Uploaded photos live outside app/static (see config.py) specifically so
# they are NEVER reachable by guessing a URL. Every request here is checked
# against who's logged in and what they're allowed to see:
#   - ID proof photos: the customer themselves, or an admin.
#   - Selfies: the customer themselves, an admin, or staff (so a pickup
#     person can visually confirm they're handing the bag to the right
#     person).
#   - Item photos: the customer themselves, an admin, or any staff member
#     (staff need these to check pickups and verify bags at the laundry).
# ---------------------------------------------------------------------------

@main_bp.route("/uploads/id-proof/<filename>")
@login_required
def id_proof_photo(filename):
    from app.models import User

    user = User.query.filter_by(id_proof_path=f"id_proofs/{filename}").first_or_404()
    if not (current_user.role == "admin" or current_user.id == user.id):
        abort(403)
    return send_from_directory(current_app.config["ID_PROOF_FOLDER"], filename)


@main_bp.route("/uploads/selfie/<filename>")
@login_required
def selfie_photo(filename):
    from app.models import User

    user = User.query.filter_by(selfie_path=f"selfies/{filename}").first_or_404()
    if not (current_user.role in ("admin", "staff") or current_user.id == user.id):
        abort(403)
    return send_from_directory(current_app.config["SELFIE_FOLDER"], filename)


@main_bp.route("/uploads/item/<filename>")
@login_required
def item_photo(filename):
    from app.models import OrderItem

    item = OrderItem.query.filter_by(photo_path=f"items/{filename}").first_or_404()
    order = item.order
    allowed = (
        current_user.role in ("admin", "staff")
        or (current_user.role == "customer" and order.customer_id == current_user.id)
    )
    if not allowed:
        abort(403)
    return send_from_directory(current_app.config["ITEM_PHOTO_FOLDER"], filename)
