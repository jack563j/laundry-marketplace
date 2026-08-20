import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_uri():
    url = os.environ.get("DATABASE_URL")
    if not url:
        return f"sqlite:///{os.path.join(BASE_DIR, 'laundry.db')}"
    # Some providers hand out "postgres://", which SQLAlchemy 2.x rejects —
    # it wants "postgresql://".
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    # In production this MUST be set via an environment variable — a guessable
    # secret key lets an attacker forge login sessions and CSRF tokens.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-before-deploying")
    IS_PRODUCTION = os.environ.get("FLASK_ENV") == "production"

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads live OUTSIDE app/static so they can never be served directly by
    # the static file route — every image is served through a login-checked
    # route instead (see app/main.py). This is what stops anyone with a
    # guessed/leaked URL from viewing another customer's ID proof.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "instance", "uploads")
    ID_PROOF_FOLDER = os.path.join(UPLOAD_FOLDER, "id_proofs")
    SELFIE_FOLDER = os.path.join(UPLOAD_FOLDER, "selfies")
    ITEM_PHOTO_FOLDER = os.path.join(UPLOAD_FOLDER, "items")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per upload

    # Session cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION  # only sent over HTTPS once deployed
    REMEMBER_COOKIE_HTTPONLY = True
