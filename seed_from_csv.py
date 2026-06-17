import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime, timezone
import uuid
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# All products from CSV
products_data = [
    # Dry Cleaning > Shirts
    {"name": "Shirt on hanger", "price": 6.45, "category": "Dry Cleaning", "subcategory": "Shirts"},
    {"name": "Delicate Shirt on hanger", "price": 7.45, "category": "Dry Cleaning", "subcategory": "Shirts"},
    {"name": "Shirt folded", "price": 6.45, "category": "Dry Cleaning", "subcategory": "Shirts"},
    
    # Dry Cleaning > Tops
    {"name": "Cardigen/Sweater", "price": 9.95, "category": "Dry Cleaning", "subcategory": "Tops"},
    {"name": "Jumper", "price": 8.95, "category": "Dry Cleaning", "subcategory": "Tops"},
    {"name": "Polo on hanger", "price": 6.45, "category": "Dry Cleaning", "subcategory": "Tops"},
    {"name": "Tshirt on hanger", "price": 5.95, "category": "Dry Cleaning", "subcategory": "Tops"},
    {"name": "Top/Blouse", "price": 8.95, "category": "Dry Cleaning", "subcategory": "Tops"},
    {"name": "Top/Blouse-Silk", "price": 9.95, "category": "Dry Cleaning", "subcategory": "Tops"},
    
    # Dry Cleaning > Bottoms
    {"name": "Shorts", "price": 6.45, "category": "Dry Cleaning", "subcategory": "Bottoms"},
    {"name": "Skirts", "price": 7.45, "category": "Dry Cleaning", "subcategory": "Bottoms"},
    {"name": "Skirts-Delicate/Pleat", "price": 8.45, "category": "Dry Cleaning", "subcategory": "Bottoms"},
    {"name": "Trousers", "price": 7.95, "category": "Dry Cleaning", "subcategory": "Bottoms"},
    {"name": "Trousers- Silk", "price": 8.95, "category": "Dry Cleaning", "subcategory": "Bottoms"},
    
    # Dry Cleaning > Suits
    {"name": "2 Piece Suit", "price": 18.45, "category": "Dry Cleaning", "subcategory": "Suits"},
    {"name": "3 Piece Suit", "price": 19.95, "category": "Dry Cleaning", "subcategory": "Suits"},
    {"name": "Dinner Suit", "price": 21.95, "category": "Dry Cleaning", "subcategory": "Suits"},
    
    # Dry Cleaning > Dresses
    {"name": "Dress", "price": 17.95, "category": "Dry Cleaning", "subcategory": "Dresses"},
    {"name": "Evening Dress", "price": 22.95, "category": "Dry Cleaning", "subcategory": "Dresses"},
    {"name": "Jump Suit", "price": 19.45, "category": "Dry Cleaning", "subcategory": "Dresses"},
    
    # Dry Cleaning > Outerwear
    {"name": "Jacket/Blazer", "price": 9.95, "category": "Dry Cleaning", "subcategory": "Outerwear"},
    {"name": "Overcoat/Raincoat", "price": 17.95, "category": "Dry Cleaning", "subcategory": "Outerwear"},
    {"name": "Overcoat full length", "price": 22.45, "category": "Dry Cleaning", "subcategory": "Outerwear"},
    {"name": "Puffer", "price": 26.95, "category": "Dry Cleaning", "subcategory": "Outerwear"},
    {"name": "Waistcoast", "price": 6.95, "category": "Dry Cleaning", "subcategory": "Outerwear"},
    
    # Dry Cleaning > Children
    {"name": "Baby clothes", "price": 4.45, "category": "Dry Cleaning", "subcategory": "Children"},
    {"name": "Children clothes", "price": 5.45, "category": "Dry Cleaning", "subcategory": "Children"},
    
    # Dry Cleaning > Accessories
    {"name": "Scraf", "price": 7.95, "category": "Dry Cleaning", "subcategory": "Accessories"},
    {"name": "Socks/Underwear", "price": 4.95, "category": "Dry Cleaning", "subcategory": "Accessories"},
    {"name": "Tie", "price": 4.95, "category": "Dry Cleaning", "subcategory": "Accessories"},
    
    # Dry Cleaning > Home Items
    {"name": "Bedsheet Single", "price": 7.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Bedsheet Double", "price": 9.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Bedsheet King", "price": 10.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Bedsheet Superking", "price": 12.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Cushion Cover Small", "price": 8.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Cushion Cover Medium", "price": 9.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Cushion Cover Large", "price": 10.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Duvet Cover Single", "price": 7.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Duvet Cover Double", "price": 9.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Duvet Cover King", "price": 10.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Duvet Cover Superking", "price": 12.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    {"name": "Pillow Case", "price": 3.45, "category": "Dry Cleaning", "subcategory": "Home Items"},
    
    # Wash & Iron > Shirts
    {"name": "Shirt on hanger", "price": 2.95, "category": "Wash & Iron", "subcategory": "Shirts"},
    {"name": "Shirt folded", "price": 2.95, "category": "Wash & Iron", "subcategory": "Shirts"},
    
    # Wash & Iron > Tops
    {"name": "Cardigan", "price": 6.45, "category": "Wash & Iron", "subcategory": "Tops"},
    {"name": "Jumper", "price": 5.95, "category": "Wash & Iron", "subcategory": "Tops"},
    {"name": "Polo/Tshirt on hanger", "price": 2.95, "category": "Wash & Iron", "subcategory": "Tops"},
    {"name": "Polo/Tshirt folded", "price": 2.45, "category": "Wash & Iron", "subcategory": "Tops"},
    {"name": "Top/Blouse", "price": 4.95, "category": "Wash & Iron", "subcategory": "Tops"},
    {"name": "Top/Blouse-Silk", "price": 5.95, "category": "Wash & Iron", "subcategory": "Tops"},
    
    # Wash & Iron > Bottoms
    {"name": "Shorts", "price": 2.95, "category": "Wash & Iron", "subcategory": "Bottoms"},
    {"name": "Skirt", "price": 4.45, "category": "Wash & Iron", "subcategory": "Bottoms"},
    {"name": "Trousers", "price": 4.95, "category": "Wash & Iron", "subcategory": "Bottoms"},
    
    # Wash & Iron > Dresses
    {"name": "Dress", "price": 8.45, "category": "Wash & Iron", "subcategory": "Dresses"},
    {"name": "Jumpsuit", "price": 10.45, "category": "Wash & Iron", "subcategory": "Dresses"},
    
    # Wash & Iron > Outerwear
    {"name": "Jacket/Blazer", "price": 6.95, "category": "Wash & Iron", "subcategory": "Outerwear"},
    {"name": "Puffer", "price": 12.95, "category": "Wash & Iron", "subcategory": "Outerwear"},
    {"name": "Overcoat/Raincoat", "price": 8.95, "category": "Wash & Iron", "subcategory": "Outerwear"},
    {"name": "Overcoat full length", "price": 11.95, "category": "Wash & Iron", "subcategory": "Outerwear"},
    {"name": "Waistcoat", "price": 4.45, "category": "Wash & Iron", "subcategory": "Outerwear"},
    
    # Wash & Iron > Children
    {"name": "Baby cloth", "price": 1.95, "category": "Wash & Iron", "subcategory": "Children"},
    {"name": "Children cloth", "price": 2.95, "category": "Wash & Iron", "subcategory": "Children"},
    
    # Wash & Iron > Accessories & Homewear
    {"name": "Scarf", "price": 2.95, "category": "Wash & Iron", "subcategory": "Accessories & Homewear"},
    {"name": "Socks/Underwear", "price": 1.45, "category": "Wash & Iron", "subcategory": "Accessories & Homewear"},
    {"name": "Tie", "price": 2.45, "category": "Wash & Iron", "subcategory": "Accessories & Homewear"},
    
    # Wash & Iron > Home Items
    {"name": "Bedsheet Single", "price": 3.95, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Bedsheet Double", "price": 5.95, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Bedsheet King", "price": 6.95, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Bedsheet Superking", "price": 7.45, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Cushion Cover Small", "price": 3.95, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Cushion Cover Medium", "price": 5.95, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Cushion Cover Large", "price": 6.95, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Duvet Cover Single", "price": 3.95, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Duvet Cover Double", "price": 5.95, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Duvet Cover King", "price": 6.95, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Duvet Cover Superking", "price": 7.95, "category": "Wash & Iron", "subcategory": "Home Items"},
    {"name": "Pillow Case", "price": 1.45, "category": "Wash & Iron", "subcategory": "Home Items"},
    
    # Ironing > Shirts
    {"name": "Shirt on hanger", "price": 2.45, "category": "Ironing", "subcategory": "Shirts"},
    {"name": "Shirt folded", "price": 2.45, "category": "Ironing", "subcategory": "Shirts"},
    
    # Ironing > Tops
    {"name": "Cardigan", "price": 3.45, "category": "Ironing", "subcategory": "Tops"},
    {"name": "Jumper", "price": 3.95, "category": "Ironing", "subcategory": "Tops"},
    {"name": "Polo/Tshirt on hanger", "price": 1.95, "category": "Ironing", "subcategory": "Tops"},
    {"name": "Polo/Tshirt folded", "price": 1.45, "category": "Ironing", "subcategory": "Tops"},
    {"name": "Top/Blouse", "price": 2.95, "category": "Ironing", "subcategory": "Tops"},
    {"name": "Top/Blouse-Silk", "price": 3.95, "category": "Ironing", "subcategory": "Tops"},
    
    # Ironing > Bottoms
    {"name": "Shorts", "price": 1.95, "category": "Ironing", "subcategory": "Bottoms"},
    {"name": "Skirt", "price": 3.45, "category": "Ironing", "subcategory": "Bottoms"},
    {"name": "Trousers", "price": 3.95, "category": "Ironing", "subcategory": "Bottoms"},
    
    # Ironing > Dresses
    {"name": "Dress", "price": 4.95, "category": "Ironing", "subcategory": "Dresses"},
    {"name": "Dress Delicate", "price": 6.45, "category": "Ironing", "subcategory": "Dresses"},
    {"name": "Dress Evening", "price": 8.45, "category": "Ironing", "subcategory": "Dresses"},
    {"name": "Jumpsuit", "price": 8.45, "category": "Ironing", "subcategory": "Dresses"},
    
    # Ironing > Outerwear
    {"name": "Waistcoat", "price": 2.95, "category": "Ironing", "subcategory": "Outerwear"},
    {"name": "Jacket/Blazer", "price": 4.95, "category": "Ironing", "subcategory": "Outerwear"},
    
    # Ironing > Children
    {"name": "Child cloth 0-8 years", "price": 1.95, "category": "Ironing", "subcategory": "Children"},
    
    # Ironing > Bedding
    {"name": "Bedsheet Single", "price": 2.95, "category": "Ironing", "subcategory": "Bedding"},
    {"name": "Bedsheet Double", "price": 4.95, "category": "Ironing", "subcategory": "Bedding"},
    {"name": "Bedsheet King", "price": 5.95, "category": "Ironing", "subcategory": "Bedding"},
    {"name": "Bedsheet Superking", "price": 6.95, "category": "Ironing", "subcategory": "Bedding"},
    {"name": "Duvet Cover Single", "price": 2.95, "category": "Ironing", "subcategory": "Bedding"},
    {"name": "Duvet Cover Double", "price": 4.95, "category": "Ironing", "subcategory": "Bedding"},
    {"name": "Duvet Cover King", "price": 5.95, "category": "Ironing", "subcategory": "Bedding"},
    {"name": "Duvet Cover Superking", "price": 6.95, "category": "Ironing", "subcategory": "Bedding"},
    {"name": "Pillow Case", "price": 1.50, "category": "Ironing", "subcategory": "Bedding"},
    
    # Household & Bulk Laundry (most without subcategories)
    {"name": "Bedspread Single Washable", "price": 9.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Bedspread Double Washable", "price": 11.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Bedspread King Washable", "price": 12.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Bedspread Superking Washable", "price": 13.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Blanket Single", "price": 12.95, "category": "Household & Bulk Laundry", "subcategory": "Popular Items"},
    {"name": "Blanket Double", "price": 16.95, "category": "Household & Bulk Laundry", "subcategory": "Popular Items"},
    {"name": "Blanket King", "price": 19.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Feather Duvet Single", "price": 19.95, "category": "Household & Bulk Laundry", "subcategory": "Bedding"},
    {"name": "Feather Duvet Double", "price": 21.95, "category": "Household & Bulk Laundry", "subcategory": "Bedding"},
    {"name": "Feather Duvet King", "price": 23.95, "category": "Household & Bulk Laundry", "subcategory": "Popular Items"},
    {"name": "Feather Duvet Superking", "price": 24.95, "category": "Household & Bulk Laundry", "subcategory": "Bedding"},
    {"name": "Mattress Protector Single", "price": 9.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Mattress Protector Double", "price": 11.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Mattress Protector King", "price": 13.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Mattress Protector Double Layer", "price": 24.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Pillow Feather", "price": 6.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Pillow Synthetic", "price": 4.95, "category": "Household & Bulk Laundry", "subcategory": None},
    {"name": "Synthetic Duvet Single", "price": 9.95, "category": "Household & Bulk Laundry", "subcategory": "Bedding"},
    {"name": "Synthetic Duvet Double", "price": 11.95, "category": "Household & Bulk Laundry", "subcategory": "Bedding"},
    {"name": "Synthetic Duvet King", "price": 13.95, "category": "Household & Bulk Laundry", "subcategory": "Popular Items"},
    {"name": "Synthetic Duvet Superking", "price": 14.95, "category": "Household & Bulk Laundry", "subcategory": "Bedding"},
    
    # Laundry
    {"name": "Mixed Wash (7KG)", "price": 14.99, "category": "Laundry", "subcategory": "Select Bag Of Service( £1.99 extra/KG )"},
    {"name": "Separate Wash (7KG)", "price": 14.99, "category": "Laundry", "subcategory": "Select Bag Of Service( £1.99 extra/KG )"},
]


async def seed_database():
    print("Starting database seeding from CSV data...")
    
    # Clear existing data
    await db.products.delete_many({})
    await db.users.delete_many({})
    await db.businesses.delete_many({})
    await db.orders.delete_many({})
    print("Cleared existing data")
    
    # Create admin user
    admin_user = {
        "id": str(uuid.uuid4()),
        "email": "support@laundry-express.co.uk",
        "password": pwd_context.hash("admin123"),
        "name": "Admin",
        "phone": "+447777367078",
        "role": "super_admin",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(admin_user)
    print("Created admin user")
    
    # Create business
    business_id = str(uuid.uuid4())
    business = {
        "id": business_id,
        "name": "Laundry Express",
        "owner_email": "support@laundry-express.co.uk",
        "pin_codes": ["CO27FQ", "CO1", "CO2", "CO3", "CO4", "CO5"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.businesses.insert_one(business)
    print("Created business: Laundry Express")
    
    # Create products from CSV data
    products_to_insert = []
    for idx, product in enumerate(products_data):
        product_doc = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "business_name": "Laundry Express",
            "service_type": "Laundry Service",
            "category": product["category"],
            "subcategory": product.get("subcategory"),
            "name": product["name"],
            "price": product["price"],
            "icon_url": None,
            "sort_order": idx,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        products_to_insert.append(product_doc)
    
    await db.products.insert_many(products_to_insert)
    print(f"Created {len(products_to_insert)} products")
    
    print("\nDatabase seeding completed!")
    print("\nCategories available:")
    categories = sorted(list(set([p["category"] for p in products_data])))
    for cat in categories:
        subcats = sorted(list(set([p.get("subcategory") for p in products_data if p["category"] == cat and p.get("subcategory")])))
        print(f"  - {cat}: {', '.join(subcats) if subcats else 'No subcategories'}")
    
    print("\nAdmin credentials:")
    print("Email: support@laundry-express.co.uk")
    print("Password: admin123")
    print("\nAvailable pin codes: CO27FQ, CO1, CO2, CO3, CO4, CO5")

if __name__ == "__main__":
    asyncio.run(seed_database())
    client.close()
