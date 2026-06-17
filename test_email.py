import asyncio
import os
from dotenv import load_dotenv
from email_service import send_order_confirmation_email

load_dotenv()

async def test_email():
    # Test order data
    test_order = {
        "order_number": 999999,
        "user_name": "Test User",
        "user_email": "er.choksimohit@gmail.com",  # Your email for testing
        "items": [
            {
                "product_name": "Test Shirt",
                "category": "Dry Cleaning",
                "subcategory": "Shirts",
                "quantity": 1,
                "price": 6.45
            }
        ],
        "total_amount": 6.45,
        "pickup_date": "2025-01-10",
        "pickup_time": "9:00 AM - 12:00 PM",
        "delivery_date": "2025-01-12",
        "delivery_time": "2:00 PM - 5:00 PM",
        "payment_method": "cod"
    }
    
    print("Testing email service...")
    print(f"Sender: {os.environ.get('SENDER_EMAIL')}")
    print(f"Recipient: {test_order['user_email']}")
    print(f"Resend API Key: {os.environ.get('RESEND_API_KEY')[:20]}...")
    
    try:
        result = await send_order_confirmation_email(test_order, test_order['user_email'])
        print(f"\n✅ Result: {result}")
        
        if result.get('status') == 'success':
            print(f"✅ Email sent successfully! Email ID: {result.get('email_id')}")
        else:
            print(f"❌ Email failed: {result.get('message')}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_email())
