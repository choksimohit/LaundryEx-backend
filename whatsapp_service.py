import os
import logging
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_WHATSAPP_TO = os.environ.get("TWILIO_WHATSAPP_TO")


def _get_client():
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise ValueError("Twilio credentials not configured")
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_whatsapp_new_order(order_doc: dict):
    if not TWILIO_WHATSAPP_TO:
        logger.warning("TWILIO_WHATSAPP_TO not set, skipping WhatsApp notification")
        return

    items_summary = ", ".join(
        f"{item['product_name']} x{item['quantity']}"
        for item in order_doc.get("items", [])[:3]
    )
    if len(order_doc.get("items", [])) > 3:
        items_summary += f" + {len(order_doc['items']) - 3} more"

    message = (
        f"🛒 *New Order #{order_doc.get('order_number')}*\n\n"
        f"👤 {order_doc.get('user_name')} ({order_doc.get('user_email')})\n"
        f"📦 {items_summary}\n"
        f"💰 Total: £{order_doc.get('total_amount', 0):.2f}\n"
        f"📅 Pickup: {order_doc.get('pickup_date')} ({order_doc.get('pickup_time')})\n"
        f"🚚 Delivery: {order_doc.get('delivery_date')} ({order_doc.get('delivery_time')})\n"
        f"💳 Payment: {order_doc.get('payment_method', '').upper()}"
    )

    client = _get_client()
    client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        to=TWILIO_WHATSAPP_TO,
        body=message
    )
    logger.info(f"WhatsApp order notification sent for order #{order_doc.get('order_number')}")


def send_whatsapp_new_user(name: str, email: str, phone: str):
    if not TWILIO_WHATSAPP_TO:
        logger.warning("TWILIO_WHATSAPP_TO not set, skipping WhatsApp notification")
        return

    message = (
        f"👤 *New Customer Registered*\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Phone: {phone or 'Not provided'}"
    )

    client = _get_client()
    client.messages.create(
        from_=TWILIO_WHATSAPP_FROM,
        to=TWILIO_WHATSAPP_TO,
        body=message
    )
    logger.info(f"WhatsApp new user notification sent for {email}")
