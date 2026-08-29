"""
WhatsApp notification service using Green API (free tier: 500 msgs/month).

Setup:
  1. Sign up at https://green-api.com
  2. Create a free instance and link your WhatsApp number
  3. Set env vars: GREEN_API_INSTANCE_ID and GREEN_API_TOKEN

If the env vars are not set, all functions silently do nothing — the app
won't crash if WhatsApp is not configured.
"""

import io
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)

GREEN_API_BASE = "https://api.green-api.com"


def _get_config():
    instance_id = current_app.config.get("GREEN_API_INSTANCE_ID", "")
    token = current_app.config.get("GREEN_API_TOKEN", "")
    return instance_id, token


def _format_phone(phone: str) -> str:
    """
    Green API requires the number in international format without '+': e.g. '919876543210@c.us'
    Assumes Indian numbers (adds 91 country code if not already present).
    """
    phone = "".join(filter(str.isdigit, phone))
    if len(phone) == 10:
        phone = "91" + phone
    return f"{phone}@c.us"


def send_whatsapp_text(phone: str, message: str) -> bool:
    """
    Send a plain text WhatsApp message to the given phone number.

    Returns True on success, False on failure (and logs the error).
    """
    instance_id, token = _get_config()
    if not instance_id or not token:
        logger.info("WhatsApp not configured — skipping text message to %s", phone)
        return False

    url = f"{GREEN_API_BASE}/waInstance{instance_id}/sendMessage/{token}"
    payload = {
        "chatId": _format_phone(phone),
        "message": message,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.error("WhatsApp text send failed: %s", exc)
        return False


def send_whatsapp_file(phone: str, file_bytes: bytes, filename: str, caption: str = "") -> bool:
    """
    Send a file (e.g. PDF invoice) as a WhatsApp attachment.

    Returns True on success, False on failure (and logs the error).
    """
    instance_id, token = _get_config()
    if not instance_id or not token:
        logger.info("WhatsApp not configured — skipping file send to %s", phone)
        return False

    url = f"{GREEN_API_BASE}/waInstance{instance_id}/sendFileByUpload/{token}"
    try:
        response = requests.post(
            url,
            data={"chatId": _format_phone(phone), "caption": caption},
            files={"file": (filename, io.BytesIO(file_bytes), "application/pdf")},
            timeout=30,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        logger.error("WhatsApp file send failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Convenience helpers for specific app events
# ---------------------------------------------------------------------------

def notify_kyc_approved(customer):
    """Customer KYC approved — they can now book a pickup."""
    send_whatsapp_text(
        customer.phone,
        f"✅ Hi {customer.name}, your ID has been verified on FreshFold!\n"
        "You can now log in and book a laundry pickup. 🧺",
    )


def notify_pickup_confirmed(customer, slot):
    """Pickup has been approved and scheduled."""
    send_whatsapp_text(
        customer.phone,
        f"📦 Hi {customer.name}, your laundry pickup is confirmed!\n"
        f"📅 Date: {slot.date.strftime('%d %b %Y')}\n"
        f"🕐 Time: {slot.start_time.strftime('%I:%M %p')} – {slot.end_time.strftime('%I:%M %p')}\n"
        f"📍 Location: {slot.location}\n\n"
        "Please keep your items ready. — FreshFold 🧺",
    )


def notify_out_for_delivery(customer, order):
    """Order is out for delivery — share OTP."""
    send_whatsapp_text(
        customer.phone,
        f"🚚 Hi {customer.name}, your laundry (Order #{order.id}) is on its way!\n\n"
        f"🔐 *Delivery OTP: {order.delivery_otp}*\n\n"
        "Please share this code with the delivery person to confirm receipt. — FreshFold 🧺",
    )


def notify_delivered_with_invoice(customer, order, invoice_bytes: bytes):
    """Order delivered — send a thank-you text + invoice PDF."""
    send_whatsapp_text(
        customer.phone,
        f"✅ Hi {customer.name}, your laundry (Order #{order.id}) has been delivered!\n"
        f"💰 Total: ₹{order.total_amount or order.computed_total:.2f}\n\n"
        "Thank you for choosing FreshFold! 🧺",
    )
    send_whatsapp_file(
        customer.phone,
        invoice_bytes,
        filename=f"FreshFold_Invoice_Order{order.id}.pdf",
        caption=f"Invoice for Order #{order.id} — FreshFold",
    )
