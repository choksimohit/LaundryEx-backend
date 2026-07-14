import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

META_WHATSAPP_TOKEN = os.environ.get("META_WHATSAPP_TOKEN")
META_PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID")
META_ADMIN_WHATSAPP = os.environ.get("META_ADMIN_WHATSAPP")  # digits only, e.g. 447911123456

META_API_URL = "https://graph.facebook.com/v20.0"


def _normalise_phone(phone: str) -> str:
    """Return E.164 digits only (no + prefix) as required by Meta API."""
    phone = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
    if phone.startswith("0"):
        phone = "44" + phone[1:]
    return phone


def _send(to: str, body: str):
    """Core send — POST to Meta WhatsApp Cloud API."""
    if not META_WHATSAPP_TOKEN or not META_PHONE_NUMBER_ID:
        logger.warning("META_WHATSAPP_TOKEN or META_PHONE_NUMBER_ID not set — skipping WhatsApp send")
        return

    to = _normalise_phone(to)
    response = httpx.post(
        f"{META_API_URL}/{META_PHONE_NUMBER_ID}/messages",
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body, "preview_url": False},
        },
        headers={
            "Authorization": f"Bearer {META_WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    response.raise_for_status()
    logger.info(f"WhatsApp sent to {to} — message id: {response.json().get('messages', [{}])[0].get('id')}")


def send_whatsapp_to_customer(phone: str, message: str):
    if not phone:
        return
    _send(phone, message)


def send_whatsapp_new_order(order_doc: dict):
    if not META_ADMIN_WHATSAPP:
        logger.warning("META_ADMIN_WHATSAPP not set — skipping new order notification")
        return

    items_summary = ", ".join(
        f"{item['product_name']} x{item['quantity']}"
        for item in order_doc.get("items", [])[:3]
    )
    if len(order_doc.get("items", [])) > 3:
        items_summary += f" + {len(order_doc['items']) - 3} more"

    message = (
        f"🛒 New Order #{order_doc.get('order_number')}\n\n"
        f"👤 {order_doc.get('user_name')} ({order_doc.get('user_email')})\n"
        f"📦 {items_summary}\n"
        f"💰 Total: £{order_doc.get('total_amount', 0):.2f}\n"
        f"📅 Pickup: {order_doc.get('pickup_date')} ({order_doc.get('pickup_time')})\n"
        f"🚚 Delivery: {order_doc.get('delivery_date')} ({order_doc.get('delivery_time')})\n"
        f"💳 Payment: {order_doc.get('payment_method', '').upper()}"
    )
    _send(META_ADMIN_WHATSAPP, message)


def send_whatsapp_new_user(name: str, email: str, phone: str):
    if not META_ADMIN_WHATSAPP:
        logger.warning("META_ADMIN_WHATSAPP not set — skipping new user notification")
        return

    message = (
        f"👤 New Customer Registered\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Phone: {phone or 'Not provided'}"
    )
    _send(META_ADMIN_WHATSAPP, message)
