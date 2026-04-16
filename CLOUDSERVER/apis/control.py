from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import os

# Database imports
from CLOUDSERVER.database.database import users_collection, db
settings_collection = db["settings"] # Ek nayi collection settings ke liye

router = APIRouter()

# 🛡️ ADMIN SECRET KEY (Apni .env me daal lena: ADMIN_SECRET=mera_super_secret_password)
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "superadmin123")

def verify_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="🚨 Unauthorized: Admins Only!")
    return True

# ==========================================
# 📥 PAYLOAD MODELS
# ==========================================
class SuspendPayload(BaseModel):
    username: str
    action: str  # "suspend" ya "unsuspend"

class MaintenancePayload(BaseModel):
    is_active: bool  # True = Website OFF (Maintenance), False = Website ON

class BroadcastPayload(BaseModel):
    message: str
    color: str  # "red", "yellow", "blue"
    is_active: bool # True = Dikhao, False = Hatao

# ==========================================
# 🛑 1. USER SUSPEND / UNSUSPEND
# ==========================================
@router.post("/suspend-user")
async def toggle_suspend_user(payload: SuspendPayload, admin: bool = Depends(verify_admin)):
    user = await users_collection.find_one({"username": payload.username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    is_suspended = True if payload.action == "suspend" else False
    await users_collection.update_one(
        {"username": payload.username}, 
        {"$set": {"is_suspended": is_suspended}}
    )
    return {"status": "success", "message": f"User {payload.username} has been {payload.action}ed."}

# ==========================================
# 🚧 2. WEBSITE MAINTENANCE (ON/OFF)
# ==========================================
@router.post("/maintenance")
async def toggle_maintenance(payload: MaintenancePayload, admin: bool = Depends(verify_admin)):
    await settings_collection.update_one(
        {"type": "maintenance"},
        {"$set": {"is_active": payload.is_active}},
        upsert=True
    )
    state = "OFF (Under Maintenance)" if payload.is_active else "ON (Live)"
    return {"status": "success", "message": f"Website is now {state}."}

# ==========================================
# 📢 3. BROADCAST MESSAGE
# ==========================================
@router.post("/broadcast")
async def manage_broadcast(payload: BroadcastPayload, admin: bool = Depends(verify_admin)):
    await settings_collection.update_one(
        {"type": "broadcast"},
        {
            "$set": {
                "message": payload.message,
                "color": payload.color,
                "is_active": payload.is_active
            }
        },
        upsert=True
    )
    state = "Published" if payload.is_active else "Stopped"
    return {"status": "success", "message": f"Broadcast has been {state}."}

# ==========================================
# 🌐 4. GET SYSTEM STATUS (PUBLIC API - FRONTEND YAHAN SE DATA LEGA)
# ==========================================
@router.get("/system-status")
async def get_system_status():
    # Frontend bina admin key ke isko call karega
    maintenance = await settings_collection.find_one({"type": "maintenance"})
    broadcast = await settings_collection.find_one({"type": "broadcast"})
    
    return {
        "maintenance": maintenance.get("is_active", False) if maintenance else False,
        "broadcast": {
            "is_active": broadcast.get("is_active", False) if broadcast else False,
            "message": broadcast.get("message", "") if broadcast else "",
            "color": broadcast.get("color", "yellow") if broadcast else "yellow"
        }
    }
  
