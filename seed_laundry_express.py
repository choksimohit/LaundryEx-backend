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
    print("Starting Laundry Express database seeding...")
    
    # Clear existing data
    await db.users.delete_many({})
    await db.businesses.delete_many({})
    await db.products.delete_many({})
    await db.orders.delete_many({})
    print("Cleared existing data")
    
    # Create admin users
    admin_users = [
        {
            "id": str(uuid.uuid4()),
            "email": "support@laundry-express.co.uk",
            "password": pwd_context.hash("admin123"),
            "name": "Super Admin",
            "phone": "+44 7777 367076",
            "role": "super_admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.users.insert_many(admin_users)
    print(f"Created {len(admin_users)} admin users")
    
    # Create business
    business = {
        "id": str(uuid.uuid4()),
        "name": "Laundry Express",
        "owner_email": "support@laundry-express.co.uk",
        "pin_codes": ["CO27FQ", "CO1", "CO2", "CO3", "CO4", "CO5"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.businesses.insert_one(business)
    print(f"Created business: {business['name']}")
    
    business_id = business["id"]
    business_name = business["name"]
    
    # Create products with Category -> Subcategory -> Product structure
    products = []
    
    # DRY CLEANING Service Type
    dry_cleaning_products = [
        # Accessories Category
        {"service_type": "Dry Cleaning", "category": "Accessories", "subcategory": None, "name": "Scraf", "price": 7.95},
        {"service_type": "Dry Cleaning", "category": "Accessories", "subcategory": None, "name": "Socks/Underwear", "price": 4.95},
        {"service_type": "Dry Cleaning", "category": "Accessories", "subcategory": None, "name": "Ties", "price": 5.95},
        {"service_type": "Dry Cleaning", "category": "Accessories", "subcategory": None, "name": "Gloves", "price": 6.95},
        
        # Bottoms Category
        {"service_type": "Dry Cleaning", "category": "Bottoms", "subcategory": None, "name": "Shorts", "price": 6.45},
        {"service_type": "Dry Cleaning", "category": "Bottoms", "subcategory": None, "name": "Skirts", "price": 7.45},
        {"service_type": "Dry Cleaning", "category": "Bottoms", "subcategory": None, "name": "Skirts-Delicate/Pleat", "price": 8.45},
        {"service_type": "Dry Cleaning", "category": "Bottoms", "subcategory": None, "name": "Trousers", "price": 7.95},
        {"service_type": "Dry Cleaning", "category": "Bottoms", "subcategory": None, "name": "Jeans", "price": 7.45},
        
        # Tops Category
        {"service_type": "Dry Cleaning", "category": "Tops", "subcategory": None, "name": "Shirt", "price": 4.95},
        {"service_type": "Dry Cleaning", "category": "Tops", "subcategory": None, "name": "Blouse", "price": 5.45},
        {"service_type": "Dry Cleaning", "category": "Tops", "subcategory": None, "name": "T-Shirt", "price": 3.95},
        {"service_type": "Dry Cleaning", "category": "Tops", "subcategory": None, "name": "Polo Shirt", "price": 4.45},
        
        # Outerwear Category
        {"service_type": "Dry Cleaning", "category": "Outerwear", "subcategory": None, "name": "Jacket", "price": 12.95},
        {"service_type": "Dry Cleaning", "category": "Outerwear", "subcategory": None, "name": "Coat", "price": 14.95},
        {"service_type": "Dry Cleaning", "category": "Outerwear", "subcategory": None, "name": "Blazer", "price": 11.95},
        
        # Dresses Category
        {"service_type": "Dry Cleaning", "category": "Dresses", "subcategory": None, "name": "Dress", "price": 12.45},
        {"service_type": "Dry Cleaning", "category": "Dresses", "subcategory": None, "name": "Evening Dress", "price": 18.95},
        {"service_type": "Dry Cleaning", "category": "Dresses", "subcategory": None, "name": "Wedding Dress", "price": 49.95},
    ]
    
    # HOUSEHOLD & BULK LAUNDRY Service Type
    household_products = [
        {"service_type": "Household & Bulk Laundry", "category": "Bedding", "subcategory": None, "name": "Single Duvet", "price": 12.95},
        {"service_type": "Household & Bulk Laundry", "category": "Bedding", "subcategory": None, "name": "Double Duvet", "price": 15.95},
        {"service_type": "Household & Bulk Laundry", "category": "Bedding", "subcategory": None, "name": "King Duvet", "price": 18.95},
        {"service_type": "Household & Bulk Laundry", "category": "Bedding", "subcategory": None, "name": "Bed Sheet", "price": 6.95},
        {"service_type": "Household & Bulk Laundry", "category": "Bedding", "subcategory": None, "name": "Pillow", "price": 5.95},
        
        {"service_type": "Household & Bulk Laundry", "category": "Curtains", "subcategory": None, "name": "Curtains (per pair)", "price": 24.95},
        {"service_type": "Household & Bulk Laundry", "category": "Curtains", "subcategory": None, "name": "Net Curtains", "price": 12.95},
        
        {"service_type": "Household & Bulk Laundry", "category": "Towels", "subcategory": None, "name": "Bath Towel", "price": 4.95},
        {"service_type": "Household & Bulk Laundry", "category": "Towels", "subcategory": None, "name": "Hand Towel", "price": 2.95},
    ]
    
    # IRONING Service Type
    ironing_products = [
        {"service_type": "Ironing", "category": "Shirts", "subcategory": None, "name": "Shirt", "price": 2.50},
        {"service_type": "Ironing", "category": "Shirts", "subcategory": None, "name": "Blouse", "price": 2.75},
        
        {"service_type": "Ironing", "category": "Trousers", "subcategory": None, "name": "Trousers", "price": 3.50},
        {"service_type": "Ironing", "category": "Trousers", "subcategory": None, "name": "Jeans", "price": 3.50},
        
        {"service_type": "Ironing", "category": "Others", "subcategory": None, "name": "Dress", "price": 4.95},
        {"service_type": "Ironing", "category": "Others", "subcategory": None, "name": "Skirt", "price": 3.50},
    ]
    
    # LAUNDRY Service Type (Wash & Fold)
    laundry_products = [
        {"service_type": "Laundry", "category": "Standard Wash", "subcategory": None, "name": "Per Kg", "price": 3.95},
        {"service_type": "Laundry", "category": "Standard Wash", "subcategory": None, "name": "Minimum 3kg", "price": 11.85},
        
        {"service_type": "Laundry", "category": "Delicate Wash", "subcategory": None, "name": "Per Kg", "price": 4.95},
    ]
    
    # WASH & IRON Service Type
    wash_iron_products = [
        {"service_type": "Wash & Iron", "category": "Standard", "subcategory": None, "name": "Per Kg", "price": 5.95},
        {"service_type": "Wash & Iron", "category": "Standard", "subcategory": None, "name": "Minimum 3kg", "price": 17.85},
    ]
    
    all_products = dry_cleaning_products + household_products + ironing_products + laundry_products + wash_iron_products
    
    for product_data in all_products:
        product_doc = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "business_name": business_name,
            **product_data,
            "icon_url": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        products.append(product_doc)
    
    await db.products.insert_many(products)
    print(f"Created {len(products)} products")
    
    print("\nDatabase seeding completed!")
    print("\nAdmin credentials:")
    print("Email: support@laundry-express.co.uk")
    print("Password: admin123")
    print("\nAvailable pin codes: CO27FQ, CO1, CO2, CO3, CO4, CO5")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
