import os
import uuid
from functools import wraps

from flask import current_app, abort
from flask_login import current_user
from PIL import Image, UnidentifiedImageError


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_upload(file_storage, folder, subfolder_label):
    """Save an uploaded image under a random filename and return the DB-stored
    path as '<subfolder_label>/<filename>' (used by the protected /uploads
    routes to look the file back up and check permissions).

    Rejects anything that isn't a real, openable image — not just files with
    an image-looking extension — so a renamed script or other payload can't
    be smuggled in through a photo upload field.
    """
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        return None

    try:
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream)
        img.verify()
        file_storage.stream.seek(0)
    except (UnidentifiedImageError, OSError):
        return None

    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, fname))
    return f"{subfolder_label}/{fname}"
