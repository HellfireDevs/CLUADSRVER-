from fastapi import APIRouter, Depends, HTTPException
from CLOUDSERVER.auth.verify import verify_api_key
from CLOUDSERVER.database.database import deploys_collection
from CLOUDSERVER.database.user import get_user_by_username  # 🔥 Naya import

router = APIRouter()

# ==========================================
# 1. FETCH ALL DEPLOYED SERVICES (For Dashboard)
# ==========================================
@router.get("/services")
async def get_my_services(username: str = Depends(verify_api_key)):
    """
    Ye API token check karegi aur us specific user ke saare bots MongoDB se nikaal kar degi.
    Sath mein premium status bhi bhejegi Paywall ke liye.
    """
    try:
        # 🔥 User ka premium status check kar rahe hain Dashboard Lock/Paywall ke liye
        user_info = await get_user_by_username(username)
        is_premium = user_info.get("is_premium", False) if user_info else False

        # MongoDB Query: Sirf wahi bots nikaal jinka "owner" ye user hai
        cursor = deploys_collection.find({"owner": username})
        bots = await cursor.to_list(length=100) # Ek baar mein max 100 bots fetch karega
        
        # MongoDB ka `_id` raw format mein JSON read nahi kar pata, isko string karna padta hai
        for bot in bots:
            bot["_id"] = str(bot["_id"])

        return {
            "status": "success",
            "user": username,
            "is_premium": is_premium,  # 🔥 Frontend Dashboard UI ko batane ke liye
            "total_services": len(bots),
            "data": bots,  # 🔥 Isko "data" kiya hai kyunki frontend response.data.data read kar raha hai
            "message": "🔥 Data fetched successfully for your dashboard!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

# ==========================================
# 2. FETCH USER PROFILE (For Profile Page)
# ==========================================
@router.get("/profile")
async def get_profile(current_user: str = Depends(verify_api_key)):
    """
    User details, Premium Status, aur Expiry Date return karega.
    """
    try:
        user_info = await get_user_by_username(current_user)
        
        if not user_info:
            raise HTTPException(status_code=404, detail="User details not found in Database!")

        return {
            "status": "success",
            "data": {
                "username": user_info.get("username"),
                "email": user_info.get("email", "Hidden"),
                "is_premium": user_info.get("is_premium", False),
                "premium_expiry": user_info.get("premium_expiry") # e.g., "2026-05-15T00:00:00"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile Fetch Error: {str(e)}")
        
