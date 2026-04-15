from datetime import datetime, timedelta
from CLOUDSERVER.database.database import users_collection

async def create_user(user_data: dict):
    """Naya user DB mein save karega"""
    # 🚀 Default setup: Naya user humesha Free hoga
    if "is_premium" not in user_data:
        user_data["is_premium"] = False
    if "premium_expiry" not in user_data:
        user_data["premium_expiry"] = None
        
    await users_collection.insert_one(user_data)
    return True

async def get_user_by_username(username: str):
    """Username se user dhoondega"""
    return await users_collection.find_one({"username": username})

async def get_user_by_email(email: str):
    """Email se user dhoondega"""
    return await users_collection.find_one({"email": email})

async def get_user_by_api_key(api_key: str):
    """API Key se verify karega (Security ke liye)"""
    return await users_collection.find_one({"api_key": api_key})
  
async def update_user_password(username: str, new_password_hash: str):
    """User ka password reset karega MongoDB mein"""
    await users_collection.update_one(
        {"username": username},
        {"$set": {"password": new_password_hash}}
    )
    return True

# ==========================================
# 👑 PREMIUM & SUBSCRIPTION SYSTEM
# ==========================================
async def update_user_premium(username: str, is_premium: bool, days: int = 0):
    """
    Telegram Bot se approval aate hi ye function hit hoga.
    User ko premium dega aur exact expiry date (aaj se X days baad ki) set kar dega.
    """
    update_data = {"is_premium": is_premium}
    
    if is_premium and days > 0:
        # Aaj ki date mein days add karke expiry date nikalo
        expiry_date = datetime.utcnow() + timedelta(days=days)
        update_data["premium_expiry"] = expiry_date
    elif not is_premium:
        # Premium khatam, expiry Null kar do
        update_data["premium_expiry"] = None

    await users_collection.update_one(
        {"username": username},
        {"$set": update_data}
    )
    return True
    
