import os
import shutil
import subprocess
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

# Tere DB aur Auth Imports
from CLOUDSERVER.database.database import users_collection, deploys_collection
from CLOUDSERVER.database.user import get_user_by_username
from CLOUDSERVER.auth.verify import verify_api_key

router = APIRouter()

# ==========================================
# 📧 EMAIL TEMPLATES (OTP & GOODBYE)
# ==========================================
def send_email(receiver_email: str, subject: str, html_content: str):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    if not sender_email or not sender_password: return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"NEX Security <{sender_email}>"
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

def send_otp_email(email: str, username: str, otp: str):
    html = f"""
    <div style="font-family: Arial; background: #050505; color: white; padding: 20px;">
        <h2 style="color: #f44336;">Account Deletion Request 🚨</h2>
        <p>Hello {username}, someone requested to delete your NEX Cloud account.</p>
        <p>If this was you, use the following OTP to confirm deletion:</p>
        <h1 style="background: #111; padding: 10px; color: #f44336; letter-spacing: 5px; text-align: center; border: 1px dashed #f44336;">{otp}</h1>
        <p style="color: gray; font-size: 12px;">If you didn't request this, ignore this email. Your account is safe.</p>
    </div>
    """
    send_email(email, "🚨 NEX Cloud - Account Deletion OTP", html)

def send_goodbye_email(email: str, username: str):
    html = f"""
    <div style="font-family: Arial; background: #050505; color: white; padding: 20px;">
        <h2 style="color: #a855f7;">Goodbye from NEX Cloud 👋</h2>
        <p>Hello {username}, your account and all associated applications have been permanently deleted.</p>
        <p>We're sad to see you go. The Bhaichara ecosystem will always welcome you back!</p>
    </div>
    """
    send_email(email, "Farewell from NEX Cloud", html)

# ==========================================
# 📥 PAYLOAD MODELS
# ==========================================
class DeleteConfirmPayload(BaseModel):
    otp: str

# ==========================================
# 🛑 API: STEP 1 - REQUEST DELETION (Generates OTP)
# ==========================================
@router.post("/request-delete-otp")
async def request_account_deletion(background_tasks: BackgroundTasks, current_user: str = Depends(verify_api_key)):
    user = await get_user_by_username(current_user)
    
    # 1. Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # 2. Save OTP in User DB Document
    await users_collection.update_one({"username": current_user}, {"$set": {"delete_otp": otp}})
    
    # 3. Send Email in Background
    if "email" in user:
        background_tasks.add_task(send_otp_email, user["email"], current_user, otp)
        
    return {"status": "success", "message": "✅ OTP sent to your registered email!"}

# ==========================================
# 💣 API: STEP 2 - CONFIRM DELETION (Nukes Account)
# ==========================================
@router.post("/confirm-delete")
async def confirm_account_deletion(payload: DeleteConfirmPayload, background_tasks: BackgroundTasks, current_user: str = Depends(verify_api_key)):
    user = await get_user_by_username(current_user)
    
    # 1. Verify OTP
    if user.get("delete_otp") != payload.otp:
        raise HTTPException(status_code=400, detail="❌ Invalid or Expired OTP!")

    # 🔥 NEW: 2. VPS SE BHI KACHRA SAAF KARO (PM2 & Folders)
    # User ke saare bots nikalo aur unhe server se delete karo
    user_bots = await deploys_collection.find({"owner": current_user}).to_list(length=100)
    for bot in user_bots:
        app_name = bot.get("pm2_name")
        folder_path = bot.get("folder_path")
        
        # PM2 aur Docker se remove karo
        if app_name:
            subprocess.run(["pm2", "delete", app_name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run(["docker", "rm", "-f", app_name.lower()], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        
        # Hard Drive se folder uda do
        if folder_path and os.path.exists(folder_path):
            shutil.rmtree(folder_path, ignore_errors=True)

    # 3. 💣 NUKE EVERYTHING FROM DATABASE
    # Remove all deployed bots belonging to user
    await deploys_collection.delete_many({"owner": current_user})
    # Remove user account
    await users_collection.delete_one({"username": current_user})

    # 4. Send Goodbye Email
    if "email" in user:
        background_tasks.add_task(send_goodbye_email, user["email"], current_user)

    return {"status": "success", "message": "💥 Account and all services deleted permanently."}
    
