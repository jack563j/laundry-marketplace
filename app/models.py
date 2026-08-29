import secrets
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def generate_otp():
    """4-digit delivery OTP. secrets (not random) so it can't be predicted."""
    return f"{secrets.randbelow(10000):04d}"

# ---------------------------------------------------------------------------
# Ordered status pipeline — index = position in the tracker stepper
# ---------------------------------------------------------------------------
ORDER_STATUSES = [
    ("AWAITING_ITEMS", "Add your items"),
    ("PENDING_PICKUP_APPROVAL", "Waiting for pickup approval"),
    ("PICKUP_APPROVED", "Pickup approved"),
    ("PICKED_UP", "Picked up"),
    ("AT_LAUNDRY", "Received at laundry"),
    ("WASHING", "Being washed"),
    ("READY", "Ready for delivery"),
    ("OUT_FOR_DELIVERY", "Out for delivery"),
    ("DELIVERED", "Delivered"),
]
ORDER_STATUS_KEYS = [s[0] for s in ORDER_STATUSES]
ORDER_STATUS_LABELS = dict(ORDER_STATUSES)
CANCELLED = "CANCELLED"


def status_index(status):
    return ORDER_STATUS_KEYS.index(status) if status in ORDER_STATUS_KEYS else -1


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)  # customer | admin | staff
    name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Customer-only KYC fields
    id_proof_path = db.Column(db.String(255))
    selfie_path = db.Column(db.String(255))  # live photo taken at signup, for identity checks at pickup
    verification_status = db.Column(db.String(20), default="PENDING")  # PENDING|APPROVED|REJECTED
    rejection_reason = db.Column(db.String(255))

    # KYC face-matching result (populated automatically after signup via Face++ API)
    kyc_face_score = db.Column(db.Float, nullable=True)          # 0.0–100.0 confidence score
    kyc_face_status = db.Column(db.String(20), default="PENDING") # PENDING|MATCHED|MISMATCH|ERROR|NO_FACE

    orders = db.relationship("Order", backref="customer", foreign_keys="Order.customer_id")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_verified_customer(self):
        return self.role == "customer" and self.verification_status == "APPROVED"


# ---------------------------------------------------------------------------
# ServiceType — laundry services with editable default prices
# ---------------------------------------------------------------------------
class ServiceType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.String(255))
    price = db.Column(db.Float, nullable=False)   # price in INR, admin-editable
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item_services = db.relationship("OrderItemService", backref="service_type")

    def __repr__(self):
        return f"<ServiceType {self.name} ₹{self.price}>"


class PickupSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=5)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))

    orders = db.relationship("Order", backref="pickup_slot")

    @property
    def booked_count(self):
        return len([o for o in self.orders if o.status != CANCELLED])

    @property
    def is_full(self):
        return self.booked_count >= self.capacity


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pickup_slot_id = db.Column(db.Integer, db.ForeignKey("pickup_slot.id"), nullable=False)
    status = db.Column(db.String(30), default="AWAITING_ITEMS")
    special_notes = db.Column(db.String(500))
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Delivery OTP — generated once the order goes OUT_FOR_DELIVERY, shown
    # only to the customer in-app, and must be read out to the delivery
    # staff and entered by them before the order can be marked DELIVERED.
    delivery_otp = db.Column(db.String(6))
    otp_attempts = db.Column(db.Integer, default=0)

    # Payment — admin sets/confirms total_amount before customer pays
    total_amount = db.Column(db.Float, nullable=True)          # in INR; null until computed
    payment_status = db.Column(db.String(20), default="UNPAID")  # UNPAID | PAID | WAIVED
    payment_id = db.Column(db.String(100), nullable=True)       # Razorpay payment_id on success

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")
    logs = db.relationship(
        "OrderStatusLog", backref="order", cascade="all, delete-orphan",
        order_by="OrderStatusLog.timestamp",
    )
    payments = db.relationship("Payment", backref="order", cascade="all, delete-orphan")
    assigned_staff = db.relationship("User", foreign_keys=[assigned_staff_id])

    @property
    def status_label(self):
        if self.status == CANCELLED:
            return "Cancelled"
        return ORDER_STATUS_LABELS.get(self.status, self.status)

    @property
    def progress_index(self):
        return status_index(self.status)

    @property
    def computed_total(self):
        """Sum of all item-service price snapshots across all items."""
        total = 0.0
        for item in self.items:
            for svc in item.services:
                total += svc.price_snapshot
        return round(total, 2)

    def advance_to(self, new_status, actor, note=None, notify_customer=True):
        self.status = new_status
        db.session.add(
            OrderStatusLog(order=self, status=new_status, changed_by_id=actor.id if actor else None, note=note)
        )
        if notify_customer and new_status != "AWAITING_ITEMS":
            label = "Cancelled" if new_status == CANCELLED else ORDER_STATUS_LABELS.get(new_status, new_status)
            notify_user(
                self.customer,
                f"Order #{self.id}: {label}",
                link=f"/customer/order/{self.id}",
            )


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    photo_path = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(120))  # e.g. "Blue shirt"
    instructions = db.Column(db.String(255))  # e.g. "Delicate wash, no bleach"
    checked_at_laundry = db.Column(db.Boolean, default=False)

    services = db.relationship("OrderItemService", backref="item", cascade="all, delete-orphan")

    @property
    def item_total(self):
        """Total cost of all services selected for this item."""
        return round(sum(s.price_snapshot for s in self.services), 2)


# ---------------------------------------------------------------------------
# OrderItemService — which services were selected for each item (price snapshotted)
# ---------------------------------------------------------------------------
class OrderItemService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey("order_item.id"), nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey("service_type.id"), nullable=False)
    price_snapshot = db.Column(db.Float, nullable=False)  # price at time of order, frozen


# ---------------------------------------------------------------------------
# Payment — Razorpay transaction record
# ---------------------------------------------------------------------------
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    razorpay_order_id = db.Column(db.String(100), nullable=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Float, nullable=False)   # in INR
    status = db.Column(db.String(20), default="CREATED")  # CREATED | SUCCESS | FAILED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OrderStatusLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    status = db.Column(db.String(30), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    note = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))  # in-app path to open when clicked
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")


def notify_user(user, message, link=None):
    db.session.add(Notification(user_id=user.id, message=message, link=link))


def notify_role(role, message, link=None):
    for user in User.query.filter_by(role=role).all():
        db.session.add(Notification(user_id=user.id, message=message, link=link))
