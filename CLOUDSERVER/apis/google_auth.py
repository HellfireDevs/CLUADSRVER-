import os
import uuid
import httpx
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from CLOUDSERVER.database.database import users_collection

router = APIRouter()

# 🔑 ENV se credentials uthao (Apni .env file me zaroor daalna)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Frontend aur Backend ke URLs (Production me isko apne Vercel/VPS domain se change kar lena)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173") 
REDIRECT_URI = f"{BACKEND_URL}/api/google/callback"

# ==========================================
# 1️⃣ LOGIN INITIATE: User ko Google ke page pe bhejega
# ==========================================
@router.get("/login")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Client ID missing in .env")
        
    url = f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=openid%20email%20profile&access_type=offline"
    return {"url": url}

# ==========================================
# 2️⃣ CALLBACK: Google wapas yahan data bhejega
# ==========================================
@router.get("/callback")
async def google_callback(code: str):
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        # Code dekar Access Token lo
        resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to authenticate with Google")
        
        access_token = resp.json().get("access_token")
        
        # Token se user ki Email aur Name nikaalo
        user_info_resp = await client.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_info_resp.json()
    
    email = user_info.get("email")
    name = user_info.get("given_name", "GoogleUser").replace(" ", "")
    
    # 🔍 Check karo user pehle se DB me hai ya nahi
    user = await users_collection.find_one({"email": email})
    
    if not user:
        # Naya user banao
        api_key = f"nex_{uuid.uuid4().hex}"
        new_user = {
            "username": name,
            "email": email,
            "password": "", # OAuth users ko password ki zaroorat nahi
            "api_key": api_key,
            "is_premium": False,
            "created_at": datetime.utcnow()
        }
        await users_collection.insert_one(new_user)
    else:
        # Purana user hai toh uski details nikaal lo
        api_key = user.get("api_key")
        name = user.get("username")

    # 🚀 Frontend pe wapas bhej do API Key ke sath
    return RedirectResponse(url=f"{FRONTEND_URL}/login?api_key={api_key}&username={name}")
  
