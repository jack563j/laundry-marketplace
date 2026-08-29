"""
KYC face-matching service using Face++ API (free: 1000 req/day, no credit card).

Setup:
  1. Sign up at https://console.faceplusplus.com
  2. Create an app → get API Key and API Secret
  3. Set env vars: FACE_API_KEY and FACE_API_SECRET

How it works:
  - Sends both uploaded photos (ID proof + selfie) to Face++
  - Face++ detects faces in each, then compares them
  - Returns a confidence score (0–100). Score ≥ 70 is considered a match.
  - Result is stored on the User model (kyc_face_score, kyc_face_status)
  - Admin still makes the final approve/reject decision — the score is a visual aid

Called in a background thread after signup so it doesn't slow down the response.
"""

import logging
import threading

import requests
from flask import current_app

logger = logging.getLogger(__name__)

FACE_COMPARE_URL = "https://api-us.faceplusplus.com/facepp/v3/compare"
SCORE_THRESHOLD = 70.0  # ≥70 → MATCHED, <70 → MISMATCH


def compare_faces_background(app, user_id: int, id_proof_path: str, selfie_path: str):
    """
    Run face comparison in a background thread so signup doesn't block.
    Writes the result directly to the DB.
    """
    thread = threading.Thread(
        target=_run_comparison,
        args=(app, user_id, id_proof_path, selfie_path),
        daemon=True,
    )
    thread.start()


def _run_comparison(app, user_id: int, id_proof_path: str, selfie_path: str):
    """Internal — runs in background thread."""
    with app.app_context():
        from app.extensions import db
        from app.models import User

        user = User.query.get(user_id)
        if not user:
            return

        result = compare_faces(id_proof_path, selfie_path, app)
        user.kyc_face_score = result.get("score")
        user.kyc_face_status = result.get("status", "ERROR")
        db.session.commit()
        logger.info(
            "KYC face check for user %d: status=%s score=%s",
            user_id, user.kyc_face_status, user.kyc_face_score,
        )


def compare_faces(id_proof_path: str, selfie_path: str, app=None) -> dict:
    """
    Compare two face photos using Face++ API.

    Returns a dict:
        {"score": float|None, "status": "MATCHED"|"MISMATCH"|"NO_FACE"|"ERROR"}
    """
    _app = app or current_app._get_current_object()
    api_key = _app.config.get("FACE_API_KEY", "")
    api_secret = _app.config.get("FACE_API_SECRET", "")

    if not api_key or not api_secret:
        logger.info("Face++ not configured — skipping KYC face check")
        return {"score": None, "status": "PENDING"}

    try:
        with open(id_proof_path, "rb") as f1, open(selfie_path, "rb") as f2:
            response = requests.post(
                FACE_COMPARE_URL,
                data={"api_key": api_key, "api_secret": api_secret},
                files={"image_file1": f1, "image_file2": f2},
                timeout=20,
            )
        data = response.json()

        if "error_message" in data:
            err = data["error_message"]
            logger.warning("Face++ error: %s", err)
            # Common error codes for missing faces
            if "NO_FACE_FOUND" in err or "EMPTY_IMAGE" in err:
                return {"score": None, "status": "NO_FACE"}
            return {"score": None, "status": "ERROR"}

        confidence = data.get("confidence", 0.0)
        status = "MATCHED" if confidence >= SCORE_THRESHOLD else "MISMATCH"
        return {"score": round(confidence, 1), "status": status}

    except FileNotFoundError as exc:
        logger.error("KYC photo file not found: %s", exc)
        return {"score": None, "status": "ERROR"}
    except Exception as exc:
        logger.error("Face++ request failed: %s", exc)
        return {"score": None, "status": "ERROR"}
