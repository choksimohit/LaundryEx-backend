import os
import asyncio
import logging
import resend
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "support@laundry-express.co.uk")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "support@laundry-express.co.uk")

logger = logging.getLogger(__name__)


def _build_items_html(order_data):
    items_html = ""
    for item in order_data["items"]:
        category = item.get('category', '')
        subcategory = item.get('subcategory', '')
        category_text = f"{category} → {subcategory}" if category and subcategory else category
        items_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">
                <div style="font-weight: 500; color: #1e293b;">
                    {item['product_name']}
                    {f'<span style="font-size: 12px; color: #64748b; margin-left: 6px;">({category_text})</span>' if category_text else ''}
                </div>
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #64748b;">
                × {item['quantity']}
            </td>
            <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right; font-weight: 500; color: #1e293b;">
                £{(item['price'] * item['quantity']):.2f}
            </td>
        </tr>
        """
    return items_html


def _build_schedule_html(order_data):
    pickup_instruction = order_data.get('pickup_instruction', '')
    delivery_instruction = order_data.get('delivery_instruction', '')
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 32px;">
        <tr>
            <td width="50%" style="padding-right: 12px;">
                <div style="background-color: #eff6ff; border-radius: 8px; padding: 20px;">
                    <div style="font-size: 14px; color: #3b82f6; font-weight: 600; margin-bottom: 8px;">🧺 Pickup</div>
                    <div style="font-size: 15px; font-weight: 600; color: #1e293b; margin-bottom: 2px;">{order_data['pickup_date']}</div>
                    <div style="font-size: 14px; color: #64748b; margin-bottom: 6px;">{order_data['pickup_time']}</div>
                    {f'<div style="font-size: 13px; color: #64748b; font-style: italic;">{pickup_instruction}</div>' if pickup_instruction else ''}
                </div>
            </td>
            <td width="50%" style="padding-left: 12px;">
                <div style="background-color: #f0fdf4; border-radius: 8px; padding: 20px;">
                    <div style="font-size: 14px; color: #22c55e; font-weight: 600; margin-bottom: 8px;">🚚 Delivery</div>
                    <div style="font-size: 15px; font-weight: 600; color: #1e293b; margin-bottom: 2px;">{order_data['delivery_date']}</div>
                    <div style="font-size: 14px; color: #64748b; margin-bottom: 6px;">{order_data['delivery_time']}</div>
                    {f'<div style="font-size: 13px; color: #64748b; font-style: italic;">{delivery_instruction}</div>' if delivery_instruction else ''}
                </div>
            </td>
        </tr>
    </table>
    """


def _build_address_html(order_data):
    return f"""
    <div style="background-color: #f1f5f9; border-radius: 8px; padding: 20px; margin-bottom: 32px;">
        <div style="font-size: 13px; color: #64748b; margin-bottom: 6px;">📍 Delivery Address</div>
        <div style="font-size: 15px; color: #1e293b; margin-bottom: 4px;">{order_data.get('address', 'N/A')}</div>
        <div style="font-size: 14px; color: #64748b;">Postcode: {order_data.get('pin_code', 'N/A')}</div>
    </div>
    """


def _build_customer_note_html(order_data):
    note = order_data.get('customer_note', '')
    if not note:
        return ''
    return f"""
    <div style="background-color: #fffbeb; border: 1px solid #fcd34d; border-radius: 8px; padding: 16px; margin-bottom: 32px;">
        <div style="font-size: 13px; font-weight: 600; color: #92400e; margin-bottom: 6px;">📝 Customer Note</div>
        <div style="font-size: 14px; color: #78350f; font-style: italic;">{note}</div>
    </div>
    """


def _build_price_summary_html(order_data):
    items_total = order_data.get('items_total', order_data['total_amount'])
    discount = order_data.get('discount_amount', 0)
    promo_code = order_data.get('promo_code', '')
    delivery_charge = order_data.get('delivery_charge', 0)
    discount_row = f'<tr><td style="padding: 6px 0; color: #16a34a; font-size: 14px;">Discount ({promo_code})</td><td style="padding: 6px 0; text-align: right; color: #16a34a;">-£{discount:.2f}</td></tr>' if discount else ''
    delivery_text = 'FREE' if not delivery_charge else f'£{delivery_charge:.2f}'
    return f"""
    <div style="background-color: #f8fafc; border-radius: 8px; padding: 20px; margin-bottom: 32px;">
        <h3 style="margin: 0 0 16px 0; font-size: 16px; color: #1e293b;">Price Summary</h3>
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td style="padding: 6px 0; color: #64748b; font-size: 14px;">Subtotal</td>
                <td style="padding: 6px 0; text-align: right; color: #1e293b;">£{items_total:.2f}</td>
            </tr>
            {discount_row}
            <tr>
                <td style="padding: 6px 0; color: #64748b; font-size: 14px;">Delivery Charge</td>
                <td style="padding: 6px 0; text-align: right; color: #1e293b;">{delivery_text}</td>
            </tr>
            <tr style="border-top: 1px solid #e2e8f0;">
                <td style="padding: 12px 0 6px; font-weight: 700; color: #1e293b; font-size: 16px;">Total</td>
                <td style="padding: 12px 0 6px; text-align: right; font-weight: 700; color: #2563eb; font-size: 18px;">£{order_data['total_amount']:.2f}</td>
            </tr>
        </table>
    </div>
    """


def generate_order_confirmation_email(order_data: Dict) -> str:
    items_html = _build_items_html(order_data)
    schedule_html = _build_schedule_html(order_data)
    address_html = _build_address_html(order_data)
    customer_note_html = _build_customer_note_html(order_data)
    price_summary_html = _build_price_summary_html(order_data)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                        <tr>
                            <td style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); padding: 40px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 32px; font-weight: 600;">Order Confirmed! 🎉</h1>
                                <p style="margin: 12px 0 0 0; color: #dbeafe; font-size: 16px;">Thank you for choosing Laundry Express</p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px;">
                                <div style="background-color: #f1f5f9; border-radius: 12px; padding: 24px; margin-bottom: 32px;">
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td>
                                                <div style="font-size: 14px; color: #64748b; margin-bottom: 4px;">Order Number</div>
                                                <div style="font-size: 24px; font-weight: 700; color: #2563eb;">#{order_data['order_number']}</div>
                                            </td>
                                            <td style="text-align: right;">
                                                <div style="font-size: 14px; color: #64748b; margin-bottom: 4px;">Payment</div>
                                                <div style="font-size: 16px; font-weight: 600; color: #1e293b; text-transform: capitalize;">{order_data['payment_method'].replace('_', ' ')}</div>
                                            </td>
                                        </tr>
                                    </table>
                                </div>

                                {address_html}
                                {customer_note_html}

                                <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #1e293b;">Order Items</h2>
                                <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-bottom: 32px;">
                                    <thead>
                                        <tr style="background-color: #f8fafc;">
                                            <th style="padding: 12px; text-align: left; font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Item</th>
                                            <th style="padding: 12px; text-align: center; font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Qty</th>
                                            <th style="padding: 12px; text-align: right; font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Price</th>
                                        </tr>
                                    </thead>
                                    <tbody>{items_html}</tbody>
                                </table>

                                {price_summary_html}

                                <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #1e293b;">Pickup & Delivery Schedule</h2>
                                {schedule_html}
                            </td>
                        </tr>
                        <tr>
                            <td style="background-color: #f8fafc; padding: 32px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0 0 8px 0; color: #64748b; font-size: 14px;">Need help? Contact us</p>
                                <p style="margin: 0; color: #2563eb; font-size: 14px; font-weight: 500;">support@laundry-express.co.uk</p>
                                <p style="margin: 16px 0 0 0; color: #94a3b8; font-size: 12px;">© 2024 Laundry Express. All rights reserved.</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html


def generate_status_update_email(order_data: Dict, new_status: str) -> str:
    status_messages = {
        "pending": "Your order has been received and is awaiting confirmation.",
        "confirmed": "Great news! Your order has been confirmed and we're preparing for pickup.",
        "processing": "Your items are being carefully processed by our team.",
        "completed": "Your order is complete and ready for delivery!",
        "cancelled": "Your order has been cancelled. If you have questions, please contact us."
    }
    status_colors = {
        "pending": "#f59e0b",
        "confirmed": "#2563eb",
        "processing": "#8b5cf6",
        "completed": "#10b981",
        "cancelled": "#ef4444"
    }
    status_icons = {
        "pending": "⏳",
        "confirmed": "✅",
        "processing": "⚙️",
        "completed": "🎉",
        "cancelled": "❌"
    }

    items_html = _build_items_html(order_data)
    schedule_html = _build_schedule_html(order_data)
    address_html = _build_address_html(order_data)
    customer_note_html = _build_customer_note_html(order_data)
    price_summary_html = _build_price_summary_html(order_data)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                        <tr>
                            <td style="background-color: {status_colors.get(new_status, '#2563eb')}; padding: 40px; text-align: center;">
                                <div style="font-size: 48px; margin-bottom: 16px;">{status_icons.get(new_status, '📦')}</div>
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600;">Order Status Updated</h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px;">
                                <div style="background-color: #f1f5f9; border-radius: 12px; padding: 24px; margin-bottom: 32px; text-align: center;">
                                    <div style="font-size: 14px; color: #64748b; margin-bottom: 8px;">Order Number</div>
                                    <div style="font-size: 28px; font-weight: 700; color: #2563eb; margin-bottom: 16px;">#{order_data['order_number']}</div>
                                    <div style="display: inline-block; background-color: {status_colors.get(new_status, '#2563eb')}; color: #ffffff; padding: 12px 24px; border-radius: 24px; font-size: 16px; font-weight: 600; text-transform: capitalize;">
                                        {new_status}
                                    </div>
                                </div>

                                <p style="font-size: 16px; line-height: 1.6; color: #475569; text-align: center; margin: 0 0 32px 0;">
                                    {status_messages.get(new_status, 'Your order status has been updated.')}
                                </p>

                                {address_html}
                                {customer_note_html}

                                <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #1e293b;">Order Items</h2>
                                <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-bottom: 32px;">
                                    <thead>
                                        <tr style="background-color: #f8fafc;">
                                            <th style="padding: 12px; text-align: left; font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Item</th>
                                            <th style="padding: 12px; text-align: center; font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Qty</th>
                                            <th style="padding: 12px; text-align: right; font-size: 13px; font-weight: 600; color: #64748b; text-transform: uppercase;">Price</th>
                                        </tr>
                                    </thead>
                                    <tbody>{items_html}</tbody>
                                </table>

                                {price_summary_html}

                                <h2 style="margin: 0 0 16px 0; font-size: 20px; color: #1e293b;">Pickup & Delivery Schedule</h2>
                                {schedule_html}
                            </td>
                        </tr>
                        <tr>
                            <td style="background-color: #f8fafc; padding: 32px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0 0 8px 0; color: #64748b; font-size: 14px;">Questions? We're here to help</p>
                                <p style="margin: 0; color: #2563eb; font-size: 14px; font-weight: 500;">support@laundry-express.co.uk</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html


def generate_admin_notification_email(order_data: Dict) -> str:
    items_html = _build_items_html(order_data)
    schedule_html = _build_schedule_html(order_data)
    customer_note_html = _build_customer_note_html(order_data)
    price_summary_html = _build_price_summary_html(order_data)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f8fafc;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8fafc; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                        <tr>
                            <td style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); padding: 40px; text-align: center;">
                                <div style="font-size: 48px; margin-bottom: 12px;">🔔</div>
                                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600;">New Order Received</h1>
                                <p style="margin: 12px 0 0 0; color: #e9d5ff; font-size: 14px;">Action required</p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px;">
                                <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 4px; margin-bottom: 32px;">
                                    <div style="font-weight: 600; color: #92400e; margin-bottom: 4px;">⚠️ Pending Action</div>
                                    <div style="color: #92400e; font-size: 14px;">Please review and confirm this order in the admin panel</div>
                                </div>

                                <div style="background-color: #f1f5f9; border-radius: 12px; padding: 24px; margin-bottom: 32px;">
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td>
                                                <div style="font-size: 13px; color: #64748b; margin-bottom: 4px;">Order Number</div>
                                                <div style="font-size: 24px; font-weight: 700; color: #7c3aed;">#{order_data['order_number']}</div>
                                            </td>
                                            <td style="text-align: right;">
                                                <div style="font-size: 13px; color: #64748b; margin-bottom: 4px;">Total</div>
                                                <div style="font-size: 24px; font-weight: 700; color: #7c3aed;">£{order_data['total_amount']:.2f}</div>
                                            </td>
                                        </tr>
                                    </table>
                                </div>

                                <h3 style="margin: 0 0 16px 0; font-size: 18px; color: #1e293b;">Customer Information</h3>
                                <div style="background-color: #f8fafc; border-radius: 8px; padding: 20px; margin-bottom: 32px;">
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td style="padding: 6px 0; color: #64748b; font-size: 14px;">Name</td>
                                            <td style="padding: 6px 0; text-align: right; color: #1e293b; font-weight: 500;">{order_data['user_name']}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #64748b; font-size: 14px;">Email</td>
                                            <td style="padding: 6px 0; text-align: right; color: #1e293b;">{order_data['user_email']}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #64748b; font-size: 14px;">Address</td>
                                            <td style="padding: 6px 0; text-align: right; color: #1e293b;">{order_data.get('address', 'N/A')}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #64748b; font-size: 14px;">Postcode</td>
                                            <td style="padding: 6px 0; text-align: right; color: #1e293b;">{order_data.get('pin_code', 'N/A')}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0; color: #64748b; font-size: 14px;">Payment</td>
                                            <td style="padding: 6px 0; text-align: right; color: #1e293b; text-transform: capitalize;">{order_data['payment_method'].replace('_', ' ')}</td>
                                        </tr>
                                    </table>
                                </div>

                                {customer_note_html}

                                <h3 style="margin: 0 0 16px 0; font-size: 18px; color: #1e293b;">Order Items</h3>
                                <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; margin-bottom: 32px;">
                                    <thead>
                                        <tr style="background-color: #f8fafc;">
                                            <th style="padding: 10px; text-align: left; font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase;">Item</th>
                                            <th style="padding: 10px; text-align: center; font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase;">Qty</th>
                                            <th style="padding: 10px; text-align: right; font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase;">Price</th>
                                        </tr>
                                    </thead>
                                    <tbody>{items_html}</tbody>
                                </table>

                                {price_summary_html}

                                <h3 style="margin: 0 0 16px 0; font-size: 18px; color: #1e293b;">Pickup & Delivery Schedule</h3>
                                {schedule_html}
                            </td>
                        </tr>
                        <tr>
                            <td style="background-color: #f8fafc; padding: 24px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0; color: #64748b; font-size: 13px;">This is an automated notification from Laundry Express Admin System</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html


async def send_order_confirmation_email(order_data: Dict, recipient_email: str):
    try:
        html_content = generate_order_confirmation_email(order_data)
        params = {
            "from": SENDER_EMAIL,
            "to": [recipient_email],
            "subject": f"Order Confirmed - #{order_data['order_number']} | Laundry Express",
            "html": html_content
        }
        email = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Order confirmation email sent to {recipient_email}, email_id: {email.get('id')}")
        return {"status": "success", "email_id": email.get("id")}
    except Exception as e:
        logger.error(f"Failed to send order confirmation email: {str(e)}")
        return {"status": "error", "message": str(e)}


async def send_status_update_email(order_data: Dict, new_status: str, recipient_email: str):
    try:
        html_content = generate_status_update_email(order_data, new_status)
        params = {
            "from": SENDER_EMAIL,
            "to": [recipient_email],
            "subject": f"Order #{order_data['order_number']} - Status Updated to {new_status.title()} | Laundry Express",
            "html": html_content
        }
        email = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Status update email sent to {recipient_email}, email_id: {email.get('id')}")
        return {"status": "success", "email_id": email.get("id")}
    except Exception as e:
        logger.error(f"Failed to send status update email: {str(e)}")
        return {"status": "error", "message": str(e)}


async def send_admin_order_notification(order_data: Dict):
    try:
        html_content = generate_admin_notification_email(order_data)
        params = {
            "from": SENDER_EMAIL,
            "to": [ADMIN_EMAIL],
            "subject": f"🔔 New Order #{order_data['order_number']} - £{order_data['total_amount']:.2f} | Laundry Express",
            "html": html_content
        }
        email = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Admin notification email sent, email_id: {email.get('id')}")
        return {"status": "success", "email_id": email.get("id")}
    except Exception as e:
        logger.error(f"Failed to send admin notification email: {str(e)}")
        return {"status": "error", "message": str(e)}


async def send_admin_new_user_notification(user_name: str, user_email: str, user_phone: str = ""):
    phone_row = f"""
                                        <tr>
                                            <td style="padding:8px 0; color:#64748b; font-size:14px; border-top:1px solid #e2e8f0;">Phone</td>
                                            <td style="padding:8px 0; color:#1e293b; border-top:1px solid #e2e8f0;"><a href="tel:{user_phone}" style="color:#0d9488; text-decoration:none;">{user_phone}</a></td>
                                        </tr>""" if user_phone else ""
    try:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
        <body style="margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif; background-color:#f8fafc;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc; padding:40px 20px;">
                <tr><td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 4px 6px rgba(0,0,0,0.05);">
                        <tr>
                            <td style="background:linear-gradient(135deg,#0f766e 0%,#0d9488 100%); padding:40px; text-align:center;">
                                <div style="font-size:48px; margin-bottom:12px;">👤</div>
                                <h1 style="margin:0; color:#ffffff; font-size:28px; font-weight:600;">New User Registered</h1>
                                <p style="margin:12px 0 0 0; color:#ccfbf1; font-size:14px;">A new customer has signed up on Laundry Express</p>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:40px;">
                                <div style="background-color:#f0fdfa; border-left:4px solid #0d9488; padding:16px; border-radius:4px; margin-bottom:32px;">
                                    <div style="font-weight:600; color:#134e4a; margin-bottom:4px;">New account created</div>
                                    <div style="color:#134e4a; font-size:14px;">You may want to reach out and welcome them.</div>
                                </div>
                                <div style="background-color:#f8fafc; border-radius:12px; padding:24px; margin-bottom:32px;">
                                    <h3 style="margin:0 0 16px 0; font-size:18px; color:#1e293b;">Customer Details</h3>
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                            <td style="padding:8px 0; color:#64748b; font-size:14px; width:40%;">Name</td>
                                            <td style="padding:8px 0; color:#1e293b; font-weight:600;">{user_name}</td>
                                        </tr>
                                        <tr>
                                            <td style="padding:8px 0; color:#64748b; font-size:14px; border-top:1px solid #e2e8f0;">Email</td>
                                            <td style="padding:8px 0; color:#1e293b; border-top:1px solid #e2e8f0;"><a href="mailto:{user_email}" style="color:#0d9488; text-decoration:none;">{user_email}</a></td>
                                        </tr>{phone_row}
                                    </table>
                                </div>
                                <div style="text-align:center;">
                                    <a href="https://laundry-express.co.uk/admin" style="display:inline-block; background:#0d9488; color:#ffffff; text-decoration:none; padding:14px 32px; border-radius:50px; font-weight:600; font-size:15px;">View in Admin Panel</a>
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td style="background-color:#f8fafc; padding:24px; text-align:center; border-top:1px solid #e2e8f0;">
                                <p style="margin:0; color:#94a3b8; font-size:13px;">Automated notification from Laundry Express</p>
                            </td>
                        </tr>
                    </table>
                </td></tr>
            </table>
        </body>
        </html>
        """
        params = {
            "from": SENDER_EMAIL,
            "to": [ADMIN_EMAIL],
            "subject": f"👤 New User Registered: {user_name} | Laundry Express",
            "html": html
        }
        email = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Admin new-user notification sent for {user_email}, email_id: {email.get('id')}")
        return {"status": "success", "email_id": email.get("id")}
    except Exception as e:
        logger.error(f"Failed to send admin new-user notification: {str(e)}")
        return {"status": "error", "message": str(e)}


def generate_review_request_email(user_name: str) -> str:
    review_link = "https://www.google.com/maps/place/Laundry+Express+Colchester/@51.8903086,0.867185,17z/data=!3m1!4b1!4m6!3m5!1s0x6743fcc25328aef:0x331b874e5e06d252!8m2!3d51.8903053!4d0.8697599!16s%2Fg%2F11xlfw4k2h"
    first_name = user_name.split()[0] if user_name else "there"
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
    <body style="margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif; background-color:#f8fafc;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f8fafc; padding:40px 20px;">
            <tr><td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:16px; overflow:hidden; box-shadow:0 4px 6px rgba(0,0,0,0.05);">
                    <tr>
                        <td style="background:linear-gradient(135deg,#1e40af 0%,#2563eb 100%); padding:40px; text-align:center;">
                            <div style="font-size:48px; margin-bottom:12px;">⭐</div>
                            <h1 style="margin:0; color:#ffffff; font-size:28px; font-weight:700;">How was your experience?</h1>
                            <p style="margin:12px 0 0 0; color:#bfdbfe; font-size:15px;">We'd love to hear from you</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:40px;">
                            <p style="font-size:16px; color:#334155; margin:0 0 16px;">Hi {first_name},</p>
                            <p style="font-size:15px; color:#64748b; line-height:1.7; margin:0 0 16px;">
                                Thank you for choosing <strong style="color:#1e293b;">Laundry Express Colchester</strong>! We hope your laundry was returned fresh, clean, and neatly folded — just the way you like it.
                            </p>
                            <p style="font-size:15px; color:#64748b; line-height:1.7; margin:0 0 32px;">
                                We're a small local business and your feedback means the world to us. It only takes 30 seconds and helps other Colchester residents discover our service. Would you mind leaving us a quick Google review?
                            </p>

                            <div style="text-align:center; margin-bottom:32px;">
                                <a href="{review_link}" style="display:inline-block; background:#2563eb; color:#ffffff; text-decoration:none; padding:16px 40px; border-radius:50px; font-weight:700; font-size:16px; letter-spacing:0.3px;">
                                    ⭐ Leave a Google Review
                                </a>
                            </div>

                            <div style="background-color:#f1f5f9; border-radius:12px; padding:20px; margin-bottom:32px; text-align:center;">
                                <p style="margin:0; color:#64748b; font-size:14px; line-height:1.6;">
                                    Just click the button above, sign in to Google, and share your honest experience.<br>
                                    <strong style="color:#1e293b;">It really does make a difference — thank you! 🙏</strong>
                                </p>
                            </div>

                            <p style="font-size:13px; color:#94a3b8; text-align:center; margin:0; border-top:1px solid #e2e8f0; padding-top:20px;">
                                If you've already left us a review — thank you so much, please ignore this email!<br>
                                Questions? Reply to this email or contact us at <a href="mailto:support@laundry-express.co.uk" style="color:#2563eb;">support@laundry-express.co.uk</a>
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color:#1e3a5f; padding:24px; text-align:center;">
                            <p style="margin:0 0 4px; color:#bfdbfe; font-size:14px; font-weight:600;">Laundry Express Colchester</p>
                            <p style="margin:0; color:#93c5fd; font-size:13px;">Doorstep laundry &amp; dry cleaning · laundry-express.co.uk</p>
                        </td>
                    </tr>
                </table>
            </td></tr>
        </table>
    </body>
    </html>
    """


async def send_review_request_to_all_users(users: list) -> dict:
    sent, failed = 0, 0
    for user in users:
        if not user.get("email"):
            continue
        try:
            html = generate_review_request_email(user.get("name", ""))
            params = {
                "from": SENDER_EMAIL,
                "to": [user["email"]],
                "subject": "How was your laundry? Leave us a quick Google review ⭐",
                "html": html,
            }
            await asyncio.to_thread(resend.Emails.send, params)
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send review request to {user.get('email')}: {e}")
            failed += 1
    return {"sent": sent, "failed": failed}


def send_password_reset_email(to_email: str, name: str, reset_link: str):
    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0; padding:0; font-family: Arial, sans-serif; background-color: #f1f5f9;">
      <div style="max-width: 560px; margin: 40px auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08);">
        <div style="background: linear-gradient(135deg, #1e40af, #2563eb); padding: 32px; text-align: center;">
          <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Laundry Express</h1>
          <p style="color: #bfdbfe; margin: 8px 0 0; font-size: 14px;">Password Reset Request</p>
        </div>
        <div style="padding: 32px;">
          <p style="color: #334155; font-size: 16px; margin: 0 0 16px;">Hi {name},</p>
          <p style="color: #64748b; font-size: 14px; line-height: 1.6; margin: 0 0 24px;">
            We received a request to reset your password. Click the button below to create a new password. This link will expire in 1 hour.
          </p>
          <div style="text-align: center; margin: 32px 0;">
            <a href="{reset_link}" style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 14px 40px; border-radius: 50px; font-weight: 600; font-size: 15px;">
              Reset Password
            </a>
          </div>
          <p style="color: #94a3b8; font-size: 12px; line-height: 1.6; margin: 24px 0 0; border-top: 1px solid #e2e8f0; padding-top: 16px;">
            If you didn't request this, you can safely ignore this email. Your password will remain unchanged.
          </p>
        </div>
      </div>
    </body>
    </html>
    """
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [to_email],
            "subject": "Reset Your Password - Laundry Express",
            "html": html
        }
        email = resend.Emails.send(params)
        logger.info(f"Password reset email sent to {to_email}, email_id: {email.get('id')}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        return {"status": "error", "message": str(e)}
