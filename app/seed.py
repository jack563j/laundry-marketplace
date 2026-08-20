from datetime import date, time, timedelta

from app.extensions import db
from app.models import User, PickupSlot


def seed_demo_data():
    if User.query.count() > 0:
        return

    admin = User(role="admin", name="Admin (You)", phone="9999900001", email="admin@example.com")
    admin.set_password("admin123")

    staff1 = User(role="staff", name="Ramesh (Laundry Staff)", phone="9999900002", email="ramesh@example.com")
    staff1.set_password("staff123")

    db.session.add_all([admin, staff1])
    db.session.commit()

    today = date.today()
    slots = [
        PickupSlot(
            date=today + timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(11, 0),
            location="Beside Shree Laundry, Main Market Road",
            capacity=6,
            created_by=admin.id,
        ),
        PickupSlot(
            date=today + timedelta(days=1),
            start_time=time(16, 0),
            end_time=time(18, 0),
            location="Beside Shree Laundry, Main Market Road",
            capacity=6,
            created_by=admin.id,
        ),
        PickupSlot(
            date=today + timedelta(days=2),
            start_time=time(9, 0),
            end_time=time(11, 0),
            location="Beside Shree Laundry, Main Market Road",
            capacity=6,
            created_by=admin.id,
        ),
    ]
    db.session.add_all(slots)
    db.session.commit()
