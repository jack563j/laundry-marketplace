from flask import Flask
from config import Config
from app.extensions import db, login_manager, csrf, limiter


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @app.after_request
    def set_security_headers(response):
        # Baseline hardening headers — cheap to set, meaningfully raise the
        # bar against clickjacking, MIME-sniffing, and referrer leakage.
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if app.config.get("IS_PRODUCTION"):
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.models import ORDER_STATUSES, CANCELLED

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        unread_count = 0
        if current_user.is_authenticated:
            from app.models import Notification
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return dict(ORDER_STATUSES=ORDER_STATUSES, CANCELLED=CANCELLED, unread_count=unread_count)

    @app.template_global()
    def item_photo_url(path):
        if not path:
            return None
        from flask import url_for
        return url_for("main.item_photo", filename=path.split("/", 1)[1])

    @app.template_global()
    def id_proof_url(path):
        if not path:
            return None
        from flask import url_for
        return url_for("main.id_proof_photo", filename=path.split("/", 1)[1])

    @app.template_global()
    def selfie_url(path):
        if not path:
            return None
        from flask import url_for
        return url_for("main.selfie_photo", filename=path.split("/", 1)[1])

    from app.auth.routes import auth_bp
    from app.customer.routes import customer_bp
    from app.admin.routes import admin_bp
    from app.staff.routes import staff_bp
    from app.main import main_bp
    from app.payment.routes import payment_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(customer_bp, url_prefix="/customer")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(staff_bp, url_prefix="/staff")
    app.register_blueprint(payment_bp, url_prefix="/payment")

    with app.app_context():
        db.create_all()
        from app.seed import seed_demo_data
        seed_demo_data()

    return app
