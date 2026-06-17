import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
from pathlib import Path
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_database():
    print("Starting database seeding...")
    
    # Clear existing data
    await db.users.delete_many({})
    await db.businesses.delete_many({})
    await db.services.delete_many({})
    await db.orders.delete_many({})
    print("Cleared existing data")
    
    # Create admin users
    admin_users = [
        {
            "id": str(uuid.uuid4()),
            "email": "admin@freshfold.com",
            "password": pwd_context.hash("admin123"),
            "name": "Super Admin",
            "phone": "+44 1234 567890",
            "role": "super_admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "email": "platform@freshfold.com",
            "password": pwd_context.hash("platform123"),
            "name": "Platform Admin",
            "phone": "+44 1234 567891",
            "role": "platform_admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "email": "business@freshfold.com",
            "password": pwd_context.hash("business123"),
            "name": "Business Admin",
            "phone": "+44 1234 567892",
            "role": "business_admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.users.insert_many(admin_users)
    print(f"Created {len(admin_users)} admin users")
    
    # Create businesses
    businesses = [
        {
            "id": str(uuid.uuid4()),
            "name": "CleanPro Laundry",
            "owner_email": "cleanpro@example.com",
            "pin_codes": ["SW1A1AA", "SW1A2AA", "W1D1NN", "WC2N5DU"],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "FreshWash Express",
            "owner_email": "freshwash@example.com",
            "pin_codes": ["E1 6AN", "E2 7HJ", "EC1A 1BB"],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Elite Dry Cleaners",
            "owner_email": "elite@example.com",
            "pin_codes": ["SW3 1AA", "SW7 2AZ", "SW1P 1AA"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.businesses.insert_many(businesses)
    print(f"Created {len(businesses)} businesses")
    
    # Create services
    services = []
    
    # Services for CleanPro Laundry
    cleanpro_services = [
        {
            "id": str(uuid.uuid4()),
            "business_id": businesses[0]["id"],
            "business_name": businesses[0]["name"],
            "name": "Standard Wash & Fold",
            "category": "wash-fold",
            "base_price": 12.99,
            "description": "Professional wash and fold service for everyday clothes",
            "image_url": "https://images.unsplash.com/photo-1627564359646-5972788cec65?crop=entropy&cs=srgb&fm=jpg&q=85",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "business_id": businesses[0]["id"],
            "business_name": businesses[0]["name"],
            "name": "Premium Dry Cleaning",
            "category": "dry-cleaning",
            "base_price": 18.50,
            "description": "Expert dry cleaning for delicate fabrics and formal wear",
            "image_url": "https://images.unsplash.com/photo-1617691120034-5bf8a1a31fbb?crop=entropy&cs=srgb&fm=jpg&q=85",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "business_id": businesses[0]["id"],
            "business_name": businesses[0]["name"],
            "name": "Express Service (24hr)",
            "category": "express",
            "base_price": 24.99,
            "description": "Fast turnaround for urgent laundry needs",
            "image_url": "https://images.unsplash.com/photo-1745613830905-552dfc3a62ba?crop=entropy&cs=srgb&fm=jpg&q=85",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Services for FreshWash Express
    freshwash_services = [
        {
            "id": str(uuid.uuid4()),
            "business_id": businesses[1]["id"],
            "business_name": businesses[1]["name"],
            "name": "Economy Wash",
            "category": "wash-fold",
            "base_price": 9.99,
            "description": "Budget-friendly wash and fold service",
            "image_url": "https://images.unsplash.com/photo-1627564359646-5972788cec65?crop=entropy&cs=srgb&fm=jpg&q=85",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "business_id": businesses[1]["id"],
            "business_name": businesses[1]["name"],
            "name": "Ironing Service",
            "category": "ironing",
            "base_price": 14.99,
            "description": "Professional ironing for crisp, wrinkle-free clothes",
            "image_url": "https://images.unsplash.com/photo-1617691120034-5bf8a1a31fbb?crop=entropy&cs=srgb&fm=jpg&q=85",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Services for Elite Dry Cleaners
    elite_services = [
        {
            "id": str(uuid.uuid4()),
            "business_id": businesses[2]["id"],
            "business_name": businesses[2]["name"],
            "name": "Luxury Dry Cleaning",
            "category": "dry-cleaning",
            "base_price": 29.99,
            "description": "Premium dry cleaning for designer and luxury garments",
            "image_url": "https://images.unsplash.com/photo-1617691120034-5bf8a1a31fbb?crop=entropy&cs=srgb&fm=jpg&q=85",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "business_id": businesses[2]["id"],
            "business_name": businesses[2]["name"],
            "name": "Alterations & Repairs",
            "category": "alterations",
            "base_price": 19.99,
            "description": "Expert tailoring and repair services",
            "image_url": "https://images.unsplash.com/photo-1677666939395-fbeb465f80d0?crop=entropy&cs=srgb&fm=jpg&q=85",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    services = cleanpro_services + freshwash_services + elite_services
    await db.services.insert_many(services)
    print(f"Created {len(services)} services")
    
    print("\\nDatabase seeding completed!")
    print("\\nAdmin credentials:")
    print("Super Admin: admin@freshfold.com / admin123")
    print("Platform Admin: platform@freshfold.com / platform123")
    print("Business Admin: business@freshfold.com / business123")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
