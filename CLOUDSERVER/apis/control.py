from fastapi import APIRouter, HTTPException, Header, Depends, BackgroundTasks
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
# 📧 EMAIL TEMPLATES & HELPERS
# ==========================================
def _send_email_smtp(receiver_email: str, subject: str, html_content: str, from_name: str):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    if not sender_email or not sender_password: return
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{sender_email}>"
    msg["To"] = receiver_email
    msg.attach(MIMEText(html_content, "html"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"🚨 [EMAIL FAILED] {str(e)}")

def send_suspension_email(receiver_email: str, username: str):
    subject = "🚨 Action Required: Account Suspended"
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #050505; color: white; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: #0a0a0a; padding: 30px; border-radius: 15px; border: 1px solid #ef4444; box-shadow: 0px 0px 20px rgba(239,68,68,0.2);">
          <h2 style="color: #ef4444; text-align: center;">Account Suspended 🛑</h2>
          <p style="font-size: 16px; color: #ddd;">Hello <b>{username}</b>,</p>
          <p style="font-size: 15px; color: #bbb;">Your NEX CLOUD account has been suspended due to a violation of our terms of service or a pending administrative review.</p>
          <p style="font-size: 15px; color: #bbb;">Your access to deploy or manage applications has been restricted. If you believe this is a mistake, please reach out to support immediately.</p>
          <div style="text-align: center; margin-top: 30px;">
             <a href="https://cluadwebsite.vercel.app/support" style="background: #ef4444; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold;">Contact Support</a>
          </div>
        </div>
      </body>
    </html>
    """
    _send_email_smtp(receiver_email, subject, html_content, "NEX Cloud Security")

def send_unsuspension_email(receiver_email: str, username: str):
    subject = "✅ Account Restored - Welcome Back!"
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #050505; color: white; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: #0a0a0a; padding: 30px; border-radius: 15px; border: 1px solid #22c55e; box-shadow: 0px 0px 20px rgba(34,197,94,0.2);">
          <h2 style="color: #22c55e; text-align: center;">Account Restored 🎉</h2>
          <p style="font-size: 16px; color: #ddd;">Hello <b>{username}</b>,</p>
          <p style="font-size: 15px; color: #bbb;">Good news! Your NEX CLOUD account has been unsuspended and fully restored.</p>
          <p style="font-size: 15px; color: #bbb;">You can now log in and continue deploying your applications without any restrictions.</p>
          <div style="text-align: center; margin-top: 30px;">
             <a href="https://cluadwebsite.vercel.app/dashboard" style="background: #22c55e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold;">Go to Dashboard</a>
          </div>
        </div>
      </body>
    </html>
    """
    _send_email_smtp(receiver_email, subject, html_content, "NEX Cloud Support")

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
async def toggle_suspend_user(payload: SuspendPayload, background_tasks: BackgroundTasks, admin: bool = Depends(verify_admin)):
    user = await users_collection.find_one({"username": payload.username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    is_suspended = True if payload.action == "suspend" else False
    
    # DB Update karo
    await users_collection.update_one(
        {"username": payload.username}, 
        {"$set": {"is_suspended": is_suspended}}
    )
    
    # Background mein email bhej do
    if "email" in user:
        if is_suspended:
            background_tasks.add_task(send_suspension_email, user["email"], payload.username)
        else:
            background_tasks.add_task(send_unsuspension_email, user["email"], payload.username)
            
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

# ==========================================
# 👥 5. GET ALL USERS (ADMIN ONLY)
# ==========================================
@router.get("/users")
async def get_all_users(admin: bool = Depends(verify_admin)):
    # Password field ko chhod kar saare users fetch karo
    users = await users_collection.find({}, {"_id": 0, "password": 0}).to_list(length=1000)
    return {"status": "success", "data": users}

# ==========================================
# 👑 6. UPDATE PREMIUM STATUS
# ==========================================
class PremiumPayload(BaseModel):
    username: str
    is_premium: bool

@router.post("/update-premium")
async def update_premium_status(payload: PremiumPayload, admin: bool = Depends(verify_admin)):
    await users_collection.update_one(
        {"username": payload.username},
        {"$set": {"is_premium": payload.is_premium}}
    )
    status_text = "Premium Granted 👑" if payload.is_premium else "Premium Revoked ❌"
    return {"status": "success", "message": f"{payload.username} is now {status_text}"}
    
