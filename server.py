from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
import stripe
import httpx
from email_service import send_order_confirmation_email, send_status_update_email, send_admin_order_notification, send_admin_new_user_notification, send_review_request_to_all_users, send_welcome_offer_to_users
from whatsapp_service import send_whatsapp_new_order, send_whatsapp_new_user

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=500)

@app.on_event("startup")
async def run_migrations():
    await db.promo_codes.update_many(
        {"code": {"$in": ["WELCOME10", "WELCOME20"]}, "group": {"$exists": False}},
        {"$set": {"group": "welcome_offer"}}
    )
api_router = APIRouter(prefix="/api")

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    phone: str
    role: str
    created_at: str

class PinCodeCheck(BaseModel):
    pin_code: str

class PinCodeResponse(BaseModel):
    available: bool
    businesses: List[dict] = []

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    business_id: str
    business_name: str
    service_type: str
    category: str
    subcategory: Optional[str] = None
    name: str
    price: float
    icon_url: Optional[str] = None
    sort_order: Optional[int] = None
    category_sort_order: Optional[int] = None
    subcategory_sort_order: Optional[int] = None

class CartItem(BaseModel):
    product_id: str
    product_name: str
    category: str
    subcategory: Optional[str] = None
    business_id: str
    business_name: str
    price: float
    quantity: int

class OrderCreate(BaseModel):
    items: List[CartItem]
    pickup_date: str
    pickup_time: str
    pickup_instruction: str
    delivery_date: str
    delivery_time: str
    delivery_instruction: str
    address: str
    pin_code: str
    payment_method: str
    total_amount: float
    delivery_charge: Optional[float] = 0
    customer_note: Optional[str] = ""
    promo_code: Optional[str] = ""
    discount_amount: Optional[float] = 0

class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    items: List[dict]
    pickup_date: str
    pickup_time: str
    delivery_date: str
    delivery_time: str
    address: str
    pin_code: str
    payment_method: str
    payment_status: str
    total_amount: float
    status: str
    created_at: str

class Business(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    owner_email: str
    pin_codes: List[str]
    created_at: str

class BusinessCreate(BaseModel):
    name: str
    owner_email: str
    pin_codes: List[str]

class ProductCreate(BaseModel):
    business_id: str
    service_type: str
    category: str
    subcategory: Optional[str] = None
    name: str
    price: float
    icon_url: Optional[str] = None
    sort_order: Optional[int] = None

class OrderStatusUpdate(BaseModel):
    status: str

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["business_admin", "platform_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@api_router.post("/auth/register")
async def register(user_data: UserRegister):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "name": user_data.name,
        "phone": user_data.phone,
        "role": "customer",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)

    try:
        await send_admin_new_user_notification(user_data.name, user_data.email, user_data.phone or "")
    except Exception as e:
        logger.error(f"Failed to send admin new-user notification: {e}")

    try:
        send_whatsapp_new_user(user_data.name, user_data.email, user_data.phone or "")
    except Exception as e:
        logger.error(f"Failed to send WhatsApp new-user notification: {e}")

    token = create_access_token({"sub": user_id, "email": user_data.email, "role": "customer"})
    return {"token": token, "user": {"id": user_id, "email": user_data.email, "name": user_data.name, "role": "customer"}}

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user["id"], "email": user["email"], "role": user["role"]})
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]}}

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"id": current_user["id"], "email": current_user["email"], "name": current_user["name"], "role": current_user["role"]}

@api_router.post("/auth/forgot-password")
async def forgot_password(data: dict):
    email = data.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        # Don't reveal if email exists
        return {"message": "If an account with that email exists, a reset link has been sent."}
    
    # Generate a reset token (JWT with short expiry)
    reset_token = jwt.encode(
        {"sub": user["id"], "email": email, "type": "reset", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        JWT_SECRET, algorithm=JWT_ALGORITHM
    )
    
    # Store token in DB
    await db.password_resets.update_one(
        {"user_id": user["id"]},
        {"$set": {"user_id": user["id"], "token": reset_token, "created_at": datetime.now(timezone.utc).isoformat(), "used": False}},
        upsert=True
    )
    
    # Send reset email
    frontend_url = os.environ.get("FRONTEND_URL", os.environ.get("REACT_APP_BACKEND_URL", "https://laundry-express.co.uk"))
    reset_link = f"{frontend_url}/reset-password?token={reset_token}"
    
    try:
        from email_service import send_password_reset_email
        send_password_reset_email(email, user.get("name", "Customer"), reset_link)
    except Exception as e:
        logger.error(f"Failed to send reset email: {e}")
    
    return {"message": "If an account with that email exists, a reset link has been sent."}

@api_router.post("/auth/reset-password")
async def reset_password(data: dict):
    token = data.get("token", "")
    new_password = data.get("password", "")
    
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and password are required")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Invalid reset token")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    
    # Check token hasn't been used
    reset_record = await db.password_resets.find_one({"user_id": user_id, "token": token, "used": False}, {"_id": 0})
    if not reset_record:
        raise HTTPException(status_code=400, detail="This reset link has already been used or is invalid")
    
    # Update password
    hashed = hash_password(new_password)
    result = await db.users.update_one({"id": user_id}, {"$set": {"password": hashed}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Mark token as used
    await db.password_resets.update_one({"user_id": user_id, "token": token}, {"$set": {"used": True}})
    
    return {"message": "Password has been reset successfully"}

@api_router.post("/pincode/check", response_model=PinCodeResponse)
async def check_pincode(data: PinCodeCheck):
    businesses = await db.businesses.find(
        {"pin_codes": data.pin_code},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "available": len(businesses) > 0,
        "businesses": businesses
    }

@api_router.get("/products")
async def get_products(business_id: Optional[str] = None, category: Optional[str] = None, subcategory: Optional[str] = None):
    query = {}
    if business_id:
        query["business_id"] = business_id
    if category:
        query["category"] = category
    if subcategory:
        query["subcategory"] = subcategory
    
    products = await db.products.find(query, {"_id": 0}).sort([("sort_order", 1), ("name", 1)]).to_list(1000)
    return products

@api_router.get("/service-types")
async def get_service_types():
    pipeline = [
        {"$group": {"_id": "$service_type"}},
        {"$project": {"_id": 0, "name": "$_id"}}
    ]
    service_types = await db.products.aggregate(pipeline).to_list(100)
    return service_types

@api_router.get("/categories")
async def get_categories():
    # Get distinct categories from products
    pipeline = [
        {"$group": {"_id": "$category"}},
        {"$project": {"_id": 0, "name": "$_id"}}
    ]
    product_categories = await db.products.aggregate(pipeline).to_list(100)
    
    # Get sort order from categories collection
    saved_orders = {}
    cat_docs = await db.categories.find({}, {"_id": 0}).to_list(100)
    for doc in cat_docs:
        saved_orders[doc["name"]] = doc.get("sort_order", 999)
    
    # Merge: use saved sort_order if available, otherwise alphabetical at end
    for cat in product_categories:
        cat["sort_order"] = saved_orders.get(cat["name"], 999)
    
    product_categories.sort(key=lambda c: (c["sort_order"], c["name"]))
    return product_categories

@api_router.get("/subcategories-order")
async def get_subcategories_order():
    subcat_docs = await db.subcategories.find({}, {"_id": 0}).to_list(500)
    return subcat_docs

@api_router.post("/orders")
async def create_order(order_data: OrderCreate, current_user: dict = Depends(get_current_user)):
    # Closure period validation: 19 Apr - 25 Apr 2026
    closure_start = "2026-04-19"
    closure_end = "2026-04-25"
    if closure_start <= order_data.pickup_date <= closure_end:
        raise HTTPException(status_code=400, detail="We are closed from 19th-25th April for scheduled maintenance. Please select a pickup date after 25th April.")
    if closure_start <= order_data.delivery_date <= closure_end:
        raise HTTPException(status_code=400, detail="We are closed from 19th-25th April for scheduled maintenance. Please select a delivery date after 25th April.")
    
    order_id = str(uuid.uuid4())
    
    # Generate 6-digit numeric order number
    last_order = await db.orders.find({}, {"_id": 0, "order_number": 1}).sort("order_number", -1).limit(1).to_list(1)
    order_number = (last_order[0]["order_number"] + 1) if last_order and "order_number" in last_order[0] else 100000
    
    # Calculate delivery charge server-side
    items_total = sum(item.price * item.quantity for item in order_data.items)
    discount = 0
    promo_code = order_data.promo_code.strip().upper() if order_data.promo_code else ""
    if promo_code:
        promo_doc = await db.promo_codes.find_one({"code": promo_code, "active": True})
        if promo_doc:
            max_uses = promo_doc.get("max_uses")
            uid = current_user["id"]
            already_used = uid in promo_doc.get("used_by", [])
            one_use = promo_doc.get("one_use_per_user", True)
            group = promo_doc.get("group")
            group_used = False
            if one_use and group and not already_used:
                group_doc = await db.promo_codes.find_one({"group": group, "used_by": uid, "code": {"$ne": promo_code}}, {"_id": 0})
                group_used = group_doc is not None
            global_limit_ok = max_uses is None or promo_doc.get("uses_count", 0) < max_uses
            if global_limit_ok and not (one_use and (already_used or group_used)):
                discount = round(items_total * promo_doc["discount_percent"] / 100, 2)
                await db.promo_codes.update_one(
                    {"code": promo_code},
                    {"$inc": {"uses_count": 1}, "$addToSet": {"used_by": current_user["id"]}}
                )
    after_discount = items_total - discount
    delivery_charge = 0 if after_discount >= 30 else 4.45
    total_with_delivery = after_discount + delivery_charge
    
    order_doc = {
        "id": order_id,
        "order_number": order_number,
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "user_email": current_user["email"],
        "items": [item.model_dump() for item in order_data.items],
        "pickup_date": order_data.pickup_date,
        "pickup_time": order_data.pickup_time,
        "pickup_instruction": order_data.pickup_instruction,
        "delivery_date": order_data.delivery_date,
        "delivery_time": order_data.delivery_time,
        "delivery_instruction": order_data.delivery_instruction,
        "address": order_data.address,
        "pin_code": order_data.pin_code,
        "payment_method": order_data.payment_method,
        "payment_status": "pending" if order_data.payment_method == "stripe" else "cod",
        "items_total": items_total,
        "promo_code": promo_code,
        "discount_amount": discount,
        "delivery_charge": delivery_charge,
        "total_amount": total_with_delivery,
        "customer_note": order_data.customer_note,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.orders.insert_one(order_doc)
    
    # Send confirmation email to customer
    try:
        await send_order_confirmation_email(order_doc, current_user["email"])
    except Exception as e:
        print(f"Failed to send customer confirmation email: {e}")
    
    # Send notification email to admin
    try:
        await send_admin_order_notification(order_doc)
    except Exception as e:
        print(f"Failed to send admin notification email: {e}")

    try:
        send_whatsapp_new_order(order_doc)
    except Exception as e:
        print(f"Failed to send WhatsApp order notification: {e}")

    return {"order_id": order_id, "order_number": order_number, "status": "success"}

@api_router.post("/payment/create-intent")
async def create_payment_intent(data: dict, current_user: dict = Depends(get_current_user)):
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(data["amount"] * 100),
            currency="gbp",
            metadata={"order_id": data.get("order_id")}
        )
        return {"client_secret": intent.client_secret}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/orders")
async def get_orders(current_user: dict = Depends(get_current_user)):
    query = {"user_id": current_user["id"]} if current_user["role"] == "customer" else {}
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return orders

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user["role"] == "customer" and order["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return order

@api_router.patch("/admin/orders/{order_id}/status")
async def update_order_status(order_id: str, data: OrderStatusUpdate, admin: dict = Depends(get_admin_user)):
    # Get the order first to send email
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    result = await db.orders.update_one(
        {"id": order_id},
        {"$set": {"status": data.status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update order dict with new status for email
    order["status"] = data.status
    
    # Send status update email to customer
    try:
        await send_status_update_email(order, data.status, order["user_email"])
    except Exception as e:
        print(f"Failed to send status update email: {e}")
    
    return {"status": "success"}

@api_router.get("/admin/businesses")
async def get_businesses(admin: dict = Depends(get_admin_user)):
    businesses = await db.businesses.find({}, {"_id": 0}).to_list(1000)
    return businesses

@api_router.post("/admin/businesses")
async def create_business(business_data: BusinessCreate, admin: dict = Depends(get_admin_user)):
    if admin["role"] not in ["platform_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Platform admin access required")
    
    business_id = str(uuid.uuid4())
    business_doc = {
        "id": business_id,
        "name": business_data.name,
        "owner_email": business_data.owner_email,
        "pin_codes": business_data.pin_codes,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.businesses.insert_one(business_doc)
    return {"business_id": business_id, "status": "success"}

@api_router.put("/admin/businesses/{business_id}")
async def update_business(business_id: str, business_data: BusinessCreate, admin: dict = Depends(get_admin_user)):
    result = await db.businesses.update_one(
        {"id": business_id},
        {"$set": {
            "name": business_data.name,
            "owner_email": business_data.owner_email,
            "pin_codes": business_data.pin_codes,
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"status": "success"}

@api_router.get("/admin/products")
async def get_admin_products(admin: dict = Depends(get_admin_user)):
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    return products

@api_router.post("/admin/products")
async def create_product(product_data: ProductCreate, admin: dict = Depends(get_admin_user)):
    business = await db.businesses.find_one({"id": product_data.business_id}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    product_id = str(uuid.uuid4())
    
    # Get max sort_order for this subcategory if not provided
    if product_data.sort_order is None:
        subcategory_filter = {"category": product_data.category, "subcategory": product_data.subcategory}
        max_product = await db.products.find(subcategory_filter, {"_id": 0}).sort("sort_order", -1).limit(1).to_list(1)
        product_data.sort_order = (max_product[0].get("sort_order", 0) + 1) if max_product else 0
    
    product_doc = {
        "id": product_id,
        "business_id": product_data.business_id,
        "business_name": business["name"],
        "service_type": product_data.service_type,
        "category": product_data.category,
        "subcategory": product_data.subcategory,
        "name": product_data.name,
        "price": product_data.price,
        "icon_url": product_data.icon_url,
        "sort_order": product_data.sort_order,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.products.insert_one(product_doc)
    return {"product_id": product_id, "status": "success"}

@api_router.put("/admin/products/{product_id}")
async def update_product(product_id: str, product_data: ProductCreate, admin: dict = Depends(get_admin_user)):
    business = await db.businesses.find_one({"id": product_data.business_id}, {"_id": 0})
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    update_doc = {
        "business_id": product_data.business_id,
        "business_name": business["name"],
        "service_type": product_data.service_type,
        "category": product_data.category,
        "subcategory": product_data.subcategory,
        "name": product_data.name,
        "price": product_data.price,
        "icon_url": product_data.icon_url,
    }
    
    if product_data.sort_order is not None:
        update_doc["sort_order"] = product_data.sort_order
    
    result = await db.products.update_one(
        {"id": product_id},
        {"$set": update_doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"status": "success"}

@api_router.delete("/admin/products/{product_id}")
async def delete_product(product_id: str, admin: dict = Depends(get_admin_user)):
    result = await db.products.delete_one({"id": product_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"status": "success"}

@api_router.get("/admin/orders")
async def get_admin_orders(admin: dict = Depends(get_admin_user)):
    orders = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return orders

@api_router.get("/admin/stats")
async def get_admin_stats(admin: dict = Depends(get_admin_user)):
    total_orders = await db.orders.count_documents({})
    total_revenue = await db.orders.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]).to_list(1)
    total_businesses = await db.businesses.count_documents({})
    total_products = await db.products.count_documents({})
    total_users = await db.users.count_documents({"role": {"$nin": ["business_admin", "platform_admin", "super_admin"]}})

    revenue = total_revenue[0]["total"] if total_revenue else 0

    return {
        "total_orders": total_orders,
        "total_revenue": revenue,
        "total_businesses": total_businesses,
        "total_products": total_products,
        "total_users": total_users,
    }

@api_router.get("/admin/users")
async def get_admin_users(admin: dict = Depends(get_admin_user)):
    users = await db.users.find(
        {"role": {"$nin": ["business_admin", "platform_admin", "super_admin"]}},
        {"_id": 0, "password": 0}
    ).sort("created_at", -1).to_list(1000)

    # Aggregate order stats per user
    order_pipeline = [
        {"$group": {
            "_id": "$user_id",
            "total_orders": {"$sum": 1},
            "first_order": {"$min": "$created_at"},
            "last_order": {"$max": "$created_at"},
            "last_address": {"$last": "$address"},
            "last_pin_code": {"$last": "$pin_code"},
        }}
    ]
    order_stats = await db.orders.aggregate(order_pipeline).to_list(1000)
    stats_by_user = {s["_id"]: s for s in order_stats}

    now = datetime.now(timezone.utc)
    result = []
    for u in users:
        uid = u.get("id")
        s = stats_by_user.get(uid, {})
        total_orders = s.get("total_orders", 0)

        # Orders per month since first order
        orders_per_month = None
        if total_orders > 0 and s.get("first_order"):
            try:
                first_dt = datetime.fromisoformat(s["first_order"].replace("Z", "+00:00"))
                months = max(1, (now - first_dt).days / 30)
                orders_per_month = round(total_orders / months, 1)
            except Exception:
                pass

        result.append({
            "id": uid,
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "phone": u.get("phone", ""),
            "created_at": u.get("created_at", ""),
            "total_orders": total_orders,
            "last_order": s.get("last_order"),
            "last_address": s.get("last_address", ""),
            "last_pin_code": s.get("last_pin_code", ""),
            "orders_per_month": orders_per_month,
            "review_request_sent_at": u.get("review_request_sent_at"),
            "welcome_offer_sent_at": u.get("welcome_offer_sent_at"),
        })

    return result


@api_router.get("/admin/review-request-preview")
async def review_request_preview(admin: dict = Depends(get_admin_user)):
    emails_with_orders = set(await db.orders.distinct("user_email"))
    users = await db.users.find(
        {"role": {"$nin": ["business_admin", "platform_admin", "super_admin"]}},
        {"_id": 0, "name": 1, "email": 1, "review_request_sent_at": 1}
    ).to_list(10000)

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    eligible = []
    for u in users:
        if u.get("email") not in emails_with_orders:
            continue
        last_sent = u.get("review_request_sent_at")
        if last_sent:
            try:
                last_sent_dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
                if last_sent_dt > thirty_days_ago:
                    continue
            except Exception:
                pass
        eligible.append({"name": u.get("name", "—"), "email": u.get("email", "")})

    return {"eligible": eligible, "count": len(eligible)}


class ReviewRequestBody(BaseModel):
    selected_emails: Optional[List[str]] = None


@api_router.post("/admin/send-review-request")
async def send_review_request(body: ReviewRequestBody, admin: dict = Depends(get_admin_user)):
    emails_with_orders = set(await db.orders.distinct("user_email"))

    users = await db.users.find(
        {"role": {"$nin": ["business_admin", "platform_admin", "super_admin"]}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "review_request_sent_at": 1}
    ).to_list(10000)

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    selected_set = set(body.selected_emails) if body.selected_emails else None

    eligible, skipped = [], 0
    for u in users:
        if u.get("email") not in emails_with_orders:
            continue
        last_sent = u.get("review_request_sent_at")
        if last_sent:
            try:
                last_sent_dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
                if last_sent_dt > thirty_days_ago:
                    skipped += 1
                    continue
            except Exception:
                pass
        if selected_set is not None and u.get("email") not in selected_set:
            continue
        eligible.append(u)

    result = await send_review_request_to_all_users(eligible)

    if eligible:
        await db.users.update_many(
            {"email": {"$in": [u["email"] for u in eligible]}},
            {"$set": {"review_request_sent_at": now.isoformat()}}
        )

    msg = f"Sent to {result['sent']} customers."
    if skipped:
        msg += f" {skipped} skipped (already emailed within 30 days)."
    return {"message": msg, "sent": result["sent"], "failed": result["failed"], "skipped": skipped}


@api_router.get("/admin/welcome-offer-preview")
async def welcome_offer_preview(admin: dict = Depends(get_admin_user)):
    emails_with_orders = set(await db.orders.distinct("user_email"))
    users = await db.users.find(
        {"role": {"$nin": ["business_admin", "platform_admin", "super_admin"]}},
        {"_id": 0, "name": 1, "email": 1, "welcome_offer_sent_at": 1}
    ).to_list(10000)

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    eligible = []
    for u in users:
        if u.get("email") in emails_with_orders:
            continue
        last_sent = u.get("welcome_offer_sent_at")
        if last_sent:
            try:
                last_sent_dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
                if last_sent_dt > thirty_days_ago:
                    continue
            except Exception:
                pass
        eligible.append({"name": u.get("name", "—"), "email": u.get("email", "")})

    return {"eligible": eligible, "count": len(eligible)}


class WelcomeOfferBody(BaseModel):
    selected_emails: Optional[List[str]] = None


@api_router.post("/admin/send-welcome-offer")
async def send_welcome_offer(body: WelcomeOfferBody, admin: dict = Depends(get_admin_user)):
    emails_with_orders = set(await db.orders.distinct("user_email"))
    users = await db.users.find(
        {"role": {"$nin": ["business_admin", "platform_admin", "super_admin"]}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "welcome_offer_sent_at": 1}
    ).to_list(10000)

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    selected_set = set(body.selected_emails) if body.selected_emails else None

    eligible, skipped = [], 0
    for u in users:
        if u.get("email") in emails_with_orders:
            continue
        last_sent = u.get("welcome_offer_sent_at")
        if last_sent:
            try:
                last_sent_dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
                if last_sent_dt > thirty_days_ago:
                    skipped += 1
                    continue
            except Exception:
                pass
        if selected_set is not None and u.get("email") not in selected_set:
            continue
        eligible.append(u)

    result = await send_welcome_offer_to_users(eligible)

    if eligible:
        await db.users.update_many(
            {"email": {"$in": [u["email"] for u in eligible]}},
            {"$set": {"welcome_offer_sent_at": now.isoformat()}}
        )

    msg = f"Sent to {result['sent']} customers."
    if skipped:
        msg += f" {skipped} skipped (already emailed within 30 days)."
    return {"message": msg, "sent": result["sent"], "failed": result["failed"], "skipped": skipped}


@api_router.get("/admin/categories")
async def get_admin_categories(admin: dict = Depends(get_admin_user)):
    # Get distinct categories from products
    pipeline = [
        {"$group": {"_id": "$category"}},
        {"$project": {"_id": 0, "name": "$_id"}}
    ]
    product_categories = await db.products.aggregate(pipeline).to_list(100)
    
    # Get sort order from categories collection
    saved_orders = {}
    cat_docs = await db.categories.find({}, {"_id": 0}).to_list(100)
    for doc in cat_docs:
        saved_orders[doc["name"]] = doc.get("sort_order", 999)
    
    for cat in product_categories:
        cat["sort_order"] = saved_orders.get(cat["name"], 999)
    
    product_categories.sort(key=lambda c: (c["sort_order"], c["name"]))
    return product_categories

@api_router.get("/admin/subcategories")
async def get_admin_subcategories(admin: dict = Depends(get_admin_user)):
    # Get distinct category+subcategory combos from products
    pipeline = [
        {"$match": {"subcategory": {"$nin": [None, ""]}}},
        {"$group": {"_id": {"category": "$category", "subcategory": "$subcategory"}}},
        {"$project": {"_id": 0, "category": "$_id.category", "name": "$_id.subcategory"}}
    ]
    product_subcats = await db.products.aggregate(pipeline).to_list(500)
    
    # Get sort order from subcategories collection
    saved_orders = {}
    subcat_docs = await db.subcategories.find({}, {"_id": 0}).to_list(500)
    for doc in subcat_docs:
        key = f"{doc['category']}|{doc['name']}"
        saved_orders[key] = doc.get("sort_order", 999)
    
    for sc in product_subcats:
        key = f"{sc['category']}|{sc['name']}"
        sc["sort_order"] = saved_orders.get(key, 999)
    
    # Sort by category then sort_order
    product_subcats.sort(key=lambda s: (s["category"], s["sort_order"], s["name"]))
    return product_subcats

@api_router.post("/admin/subcategories/reorder")
async def reorder_subcategories(data: dict, admin: dict = Depends(get_admin_user)):
    updates = data.get("updates", [])
    for update in updates:
        name = update.get("name")
        category = update.get("category")
        sort_order = update.get("sort_order")
        if name and category and sort_order is not None:
            await db.subcategories.update_one(
                {"name": name, "category": category},
                {"$set": {"name": name, "category": category, "sort_order": sort_order}},
                upsert=True
            )
    return {"status": "success", "updated": len(updates)}

@api_router.post("/admin/categories/reorder")
async def reorder_categories(data: dict, admin: dict = Depends(get_admin_user)):
    updates = data.get("updates", [])
    for update in updates:
        name = update.get("name")
        sort_order = update.get("sort_order")
        if name and sort_order is not None:
            await db.categories.update_one(
                {"name": name},
                {"$set": {"name": name, "sort_order": sort_order}},
                upsert=True
            )
    return {"status": "success", "updated": len(updates)}

@api_router.post("/admin/products/reorder")
async def reorder_products(data: dict, admin: dict = Depends(get_admin_user)):
    updates = data.get("updates", [])
    
    for update in updates:
        product_id = update.get("id")
        sort_order = update.get("sort_order")
        
        if product_id and sort_order is not None:
            await db.products.update_one(
                {"id": product_id},
                {"$set": {"sort_order": sort_order}}
            )
    
    return {"status": "success", "updated": len(updates)}

@api_router.post("/admin/subcategories/rename")
async def rename_subcategory(data: dict, admin: dict = Depends(get_admin_user)):
    old_name = data.get("old_name", "").strip()
    new_name = data.get("new_name", "").strip()
    category = data.get("category", "").strip()
    
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="Both old and new subcategory names are required")
    
    query = {"subcategory": old_name}
    if category:
        query["category"] = category
    
    result = await db.products.update_many(query, {"$set": {"subcategory": new_name}})
    return {"status": "success", "updated": result.modified_count}

INDEXNOW_KEY = "3e2b1635fee949728a88f3e88cff1780"

@api_router.get("/admin/backup")
async def download_backup(admin: dict = Depends(get_admin_user)):
    import json as json_module
    collections_to_backup = ["users", "products", "orders", "categories", "subcategories", "businesses", "password_resets"]
    backup = {}
    for col_name in collections_to_backup:
        docs = await db[col_name].find({}, {"_id": 0}).to_list(10000)
        backup[col_name] = docs
    
    backup["_meta"] = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "collections": list(backup.keys()),
        "total_documents": sum(len(v) for k, v in backup.items() if k != "_meta")
    }
    
    json_str = json_module.dumps(backup, indent=2, default=str)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=laundry-express-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"}
    )

@api_router.get("/indexnow-key")
async def get_indexnow_key():
    return Response(content=INDEXNOW_KEY, media_type="text/plain")

@api_router.post("/admin/indexnow/submit")
async def submit_indexnow(data: dict, admin: dict = Depends(get_admin_user)):
    base_url = data.get("host", "https://laundry-express.co.uk")
    urls = data.get("urls", [])
    
    if not urls:
        # Default: submit all public pages
        urls = [
            f"{base_url}/",
            f"{base_url}/services",
            f"{base_url}/order",
            f"{base_url}/login",
            f"{base_url}/register",
            f"{base_url}/sitemap",
        ]
    
    payload = {
        "host": base_url.replace("https://", "").replace("http://", ""),
        "key": INDEXNOW_KEY,
        "keyLocation": f"{base_url}/{INDEXNOW_KEY}.txt",
        "urlList": urls
    }
    
    results = {}
    engines = [
        ("Bing", "https://api.indexnow.org/IndexNow"),
    ]
    
    async with httpx.AsyncClient(timeout=15) as client:
        for name, endpoint in engines:
            try:
                resp = await client.post(endpoint, json=payload, headers={"Content-Type": "application/json"})
                results[name] = {"status": resp.status_code, "ok": resp.status_code in [200, 202]}
            except Exception as e:
                results[name] = {"status": "error", "message": str(e)}
    
    return {"submitted_urls": len(urls), "results": results}

GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
# Place ID from: https://www.google.com/maps/place/LAUNDRY+EXPRESS+COLCHESTER
GOOGLE_PLACE_ID = os.environ.get("GOOGLE_PLACE_ID", "")



@api_router.get("/reviews")
async def get_google_reviews():
    # Return cached reviews if fresh (< 1 hour old)
    cached = await db.cache.find_one({"key": "google_reviews"}, {"_id": 0})
    if cached:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(cached["fetched_at"])).total_seconds()
        if age < 3600:
            return {"reviews": cached["reviews"], "rating": cached.get("rating"), "total_ratings": cached.get("total_ratings"), "source": "cache"}

    if not GOOGLE_PLACES_API_KEY or not GOOGLE_PLACE_ID:
        return {"reviews": [], "rating": None, "total_ratings": None, "source": "unconfigured"}

    try:
        async with httpx.AsyncClient(timeout=10) as client_http:
            url = f"https://places.googleapis.com/v1/places/{GOOGLE_PLACE_ID}"
            headers = {
                "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
                "X-Goog-FieldMask": "reviews,rating,userRatingCount,displayName"
            }
            resp = await client_http.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        raw_reviews = sorted(
            data.get("reviews", []),
            key=lambda r: r.get("publishTime", ""),
            reverse=True
        )
        reviews = []
        for r in raw_reviews:
            reviews.append({
                "author": r.get("authorAttribution", {}).get("displayName", "Anonymous"),
                "author_photo": r.get("authorAttribution", {}).get("photoUri", ""),
                "rating": r.get("rating", 5),
                "text": r.get("text", {}).get("text", ""),
                "relative_time": r.get("relativePublishTimeDescription", ""),
            })

        payload = {
            "key": "google_reviews",
            "reviews": reviews,
            "rating": data.get("rating"),
            "total_ratings": data.get("userRatingCount"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.cache.update_one({"key": "google_reviews"}, {"$set": payload}, upsert=True)
        return {"reviews": reviews, "rating": data.get("rating"), "total_ratings": data.get("userRatingCount"), "source": "live"}
    except Exception as e:
        logger.error(f"Failed to fetch Google reviews: {e}")
        return {"reviews": [], "rating": None, "total_ratings": None, "source": "error"}


@api_router.get("/sitemap-xml")
async def sitemap_xml():
    base_url = os.environ.get("BASE_URL", "https://www.laundry-express.co.uk")
    pages = [
        {"loc": "/", "priority": "1.0", "changefreq": "weekly"},
        {"loc": "/services", "priority": "0.9", "changefreq": "weekly"},
        {"loc": "/order", "priority": "0.9", "changefreq": "weekly"},
        {"loc": "/blog", "priority": "0.8", "changefreq": "weekly"},
        {"loc": "/contact", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/terms", "priority": "0.3", "changefreq": "yearly"},
        {"loc": "/privacy", "priority": "0.3", "changefreq": "yearly"},
    ]
    posts = await db.blog_posts.find(
        {"status": "published"}, {"_id": 0, "slug": 1, "updated_at": 1, "created_at": 1}
    ).to_list(1000)
    urls = ""
    for p in pages:
        urls += f"""  <url>
    <loc>{base_url}{p['loc']}</loc>
    <changefreq>{p['changefreq']}</changefreq>
    <priority>{p['priority']}</priority>
  </url>\n"""
    for post in posts:
        lastmod = str(post.get("updated_at") or post.get("created_at") or "")[:10]
        lastmod_tag = f"\n    <lastmod>{lastmod}</lastmod>" if lastmod else ""
        urls += f"""  <url>
    <loc>{base_url}/blog/{post['slug']}</loc>{lastmod_tag}
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>\n"""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}</urlset>"""
    return Response(content=xml, media_type="application/xml")

import re as _re

class BlogPostCreate(BaseModel):
    title: str
    content: str
    excerpt: Optional[str] = None
    cover_image_url: Optional[str] = None
    meta_description: Optional[str] = None
    status: str = "draft"

@api_router.get("/blog")
async def get_blog_posts():
    posts = await db.blog_posts.find({"status": "published"}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return posts

@api_router.get("/blog/{slug}")
async def get_blog_post(slug: str):
    post = await db.blog_posts.find_one({"slug": slug, "status": "published"}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@api_router.get("/admin/blog")
async def get_admin_blog_posts(admin: dict = Depends(get_admin_user)):
    posts = await db.blog_posts.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return posts

@api_router.post("/admin/blog")
async def create_blog_post(post_data: BlogPostCreate, admin: dict = Depends(get_admin_user)):
    post_id = str(uuid.uuid4())
    slug = _re.sub(r'[^a-z0-9-]', '', post_data.title.lower().replace(' ', '-'))
    existing = await db.blog_posts.find_one({"slug": slug})
    if existing:
        slug = f"{slug}-{post_id[:8]}"
    post_doc = {
        "id": post_id,
        "title": post_data.title,
        "slug": slug,
        "content": post_data.content,
        "excerpt": post_data.excerpt or post_data.content[:160],
        "cover_image_url": post_data.cover_image_url,
        "meta_description": post_data.meta_description or post_data.excerpt or post_data.content[:160],
        "status": post_data.status,
        "author": admin["name"],
        "author_id": admin["id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.blog_posts.insert_one(post_doc)
    return {"post_id": post_id, "slug": slug, "status": "success"}

@api_router.put("/admin/blog/{post_id}")
async def update_blog_post(post_id: str, post_data: BlogPostCreate, admin: dict = Depends(get_admin_user)):
    slug = _re.sub(r'[^a-z0-9-]', '', post_data.title.lower().replace(' ', '-'))
    result = await db.blog_posts.update_one(
        {"id": post_id},
        {"$set": {
            "title": post_data.title,
            "slug": slug,
            "content": post_data.content,
            "excerpt": post_data.excerpt or post_data.content[:160],
            "cover_image_url": post_data.cover_image_url,
            "meta_description": post_data.meta_description or post_data.excerpt or post_data.content[:160],
            "status": post_data.status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"status": "success"}

@api_router.delete("/admin/blog/{post_id}")
async def delete_blog_post(post_id: str, admin: dict = Depends(get_admin_user)):
    result = await db.blog_posts.delete_one({"id": post_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"status": "success"}

@api_router.post("/promo/validate")
async def validate_promo_code(data: dict, current_user: dict = Depends(get_current_user)):
    code = (data.get("code") or "").strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="No code provided")
    promo = await db.promo_codes.find_one({"code": code, "active": True}, {"_id": 0})
    if not promo:
        raise HTTPException(status_code=404, detail="Invalid or inactive promo code")
    max_uses = promo.get("max_uses")
    if max_uses is not None and promo.get("uses_count", 0) >= max_uses:
        raise HTTPException(status_code=400, detail="Promo code has reached its usage limit")
    if promo.get("one_use_per_user", True):
        uid = current_user["id"]
        if uid in promo.get("used_by", []):
            raise HTTPException(status_code=400, detail="You have already used this promo code")
        group = promo.get("group")
        if group:
            group_used = await db.promo_codes.find_one({"group": group, "used_by": uid}, {"_id": 0, "code": 1})
            if group_used:
                raise HTTPException(status_code=400, detail=f"You have already used a welcome offer ({group_used['code']})")
    return {"code": promo["code"], "discount_percent": promo["discount_percent"], "description": promo.get("description", "")}


class PromoCodeCreate(BaseModel):
    code: str
    discount_percent: float
    description: Optional[str] = ""
    max_uses: Optional[int] = None
    active: bool = True
    one_use_per_user: bool = True
    group: Optional[str] = None


@api_router.get("/admin/promo-codes")
async def get_promo_codes(admin: dict = Depends(get_admin_user)):
    codes = await db.promo_codes.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return codes


@api_router.get("/admin/promo-codes/stats")
async def get_promo_stats(admin: dict = Depends(get_admin_user)):
    pipeline = [
        {"$match": {"promo_code": {"$ne": ""}}},
        {"$group": {
            "_id": "$promo_code",
            "order_count": {"$sum": 1},
            "total_revenue": {"$sum": "$total_amount"},
            "total_discount": {"$sum": "$discount_amount"},
            "first_used": {"$min": "$created_at"},
            "last_used": {"$max": "$created_at"},
            "orders": {"$push": {
                "order_number": "$order_number",
                "user_name": "$user_name",
                "user_email": "$user_email",
                "total_amount": "$total_amount",
                "discount_amount": "$discount_amount",
                "created_at": "$created_at",
                "status": "$status",
            }}
        }}
    ]
    results = await db.orders.aggregate(pipeline).to_list(1000)
    stats_by_code = {r["_id"]: r for r in results}

    total_promo_orders = sum(r["order_count"] for r in results)
    total_discount_given = round(sum(r["total_discount"] for r in results), 2)
    best_code = max(results, key=lambda r: r["order_count"])["_id"] if results else None

    return {
        "by_code": {k: {**v, "_id": None} for k, v in stats_by_code.items()},
        "summary": {
            "total_promo_orders": total_promo_orders,
            "total_discount_given": total_discount_given,
            "best_code": best_code,
        }
    }


@api_router.post("/admin/promo-codes")
async def create_promo_code(data: PromoCodeCreate, admin: dict = Depends(get_admin_user)):
    code = data.code.strip().upper()
    existing = await db.promo_codes.find_one({"code": code})
    if existing:
        raise HTTPException(status_code=400, detail="Promo code already exists")
    doc = {
        "id": str(uuid.uuid4()),
        "code": code,
        "discount_percent": data.discount_percent,
        "description": data.description,
        "max_uses": data.max_uses,
        "uses_count": 0,
        "used_by": [],
        "active": data.active,
        "one_use_per_user": data.one_use_per_user,
        "group": data.group,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.promo_codes.insert_one(doc)
    doc.pop("_id", None)
    return {"status": "success", "code": doc}


@api_router.patch("/admin/promo-codes/{code_id}")
async def update_promo_code(code_id: str, data: dict, admin: dict = Depends(get_admin_user)):
    allowed = {k: v for k, v in data.items() if k in ("active", "discount_percent", "description", "max_uses", "group", "one_use_per_user")}
    if not allowed:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    result = await db.promo_codes.update_one({"id": code_id}, {"$set": allowed})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return {"status": "success"}


@api_router.delete("/admin/promo-codes/{code_id}")
async def delete_promo_code(code_id: str, admin: dict = Depends(get_admin_user)):
    result = await db.promo_codes.delete_one({"id": code_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return {"status": "success"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()