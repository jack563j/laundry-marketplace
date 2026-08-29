from datetime import date, time, timedelta

from app.extensions import db
from app.models import User, PickupSlot, ServiceType


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

    # ---------------------------------------------------------------------------
    # Default laundry service types with prices (admin can edit these later)
    # ---------------------------------------------------------------------------
    if ServiceType.query.count() == 0:
        services = [
            ServiceType(name="Wash",           description="Machine wash + spin dry",          price=30.0),
            ServiceType(name="Iron",            description="Steam iron / press",               price=20.0),
            ServiceType(name="Wash & Iron",     description="Machine wash + steam iron",        price=45.0),
            ServiceType(name="Dry Clean",       description="Professional dry cleaning",        price=120.0),
            ServiceType(name="Fold",            description="Neat folding after wash",          price=10.0),
            ServiceType(name="Stain Removal",   description="Targeted stain treatment",         price=50.0),
            ServiceType(name="Delicate Wash",   description="Hand wash for delicate fabrics",   price=60.0),
            ServiceType(name="Bleach",          description="Whitening bleach treatment",       price=40.0),
            ServiceType(name="Curtains/Drapes", description="Wash + iron for curtains/drapes",  price=150.0),
        ]
        db.session.add_all(services)
        db.session.commit()
