from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import os
import hashlib
from dotenv import load_dotenv
import httpx # 🛡️ NEW: Turnstile verify karne ke liye
import requests # 📍 NEW: IP se location nikalne ke liye
from datetime import datetime # 🕒 NEW: Login time ke liye

# 🚀 Naya MongoDB Import
from CLOUDSERVER.database.user import create_user, get_user_by_username, get_user_by_email, update_user_password

load_dotenv()

router = APIRouter()

# ==========================================
# 🧠 TEMP STORAGE & SECURITY SETUP
# ==========================================
TEMP_OTP_STORE = {} # Jab tak OTP verify nahi hota, data memory mein rahega

# 🛡️ Smart Email Normalizer (Strictly @gmail.com & Dot/Plus trick killer)
def sanitize_email(email: str) -> str:
    email = email.lower().strip()
    if '@' not in email:
        raise HTTPException(status_code=400, detail="Invalid email format!")
        
    username, domain = email.split('@', 1)

    # 🔥 STRICT GMAIL POLICY: Sirf gmail allow karenge, baaki sab bhaad mein jaye!
    if domain not in ["gmail.com", "googlemail.com"]:
        raise HTTPException(status_code=400, detail="❌ Only @gmail.com addresses are allowed!")

    # Gmail Dot aur Plus trick fixer
    username = username.split('+')[0]
    username = username.replace('.', '')
    domain = "gmail.com"

    return f"{username}@{domain}"

# Password Hashing
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# 🤖 CLOUDFLARE TURNSTILE VERIFICATION
# ==========================================
async def verify_turnstile(token: str):
    secret = os.getenv("CLOUDFLARE_SECRET_KEY")
    if not secret:
        print("⚠️ Warning: CLOUDFLARE_SECRET_KEY is missing in .env. Skipping captcha check.")
        return True 

    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data={
            "secret": secret,
            "response": token
        })
        res = response.json()
        return res.get("success", False)

# ==========================================
# 📧 EMAIL TEMPLATES (OTP, ALERTS, WELCOME)
# ==========================================
def send_otp_email(receiver_email: str, username: str, otp: int):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    if not sender_email or not sender_password: return

    subject = "☁️ Welcome! Verify Your Cloud API Account"
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1);">
          <h2 style="color: #4CAF50; text-align: center;">Welcome to Custom Cloud Engine! 🚀</h2>
          <p style="color: #333; font-size: 16px;">Hello <b>{username}</b>,</p>
          <p style="color: #555; font-size: 15px;">Thank you for registering. To complete your setup, please use the following One-Time Password (OTP):</p>
          <div style="text-align: center; margin: 30px 0;">
            <span style="font-size: 28px; font-weight: bold; background: #eee; padding: 10px 20px; border-radius: 5px; letter-spacing: 5px; color: #333;">
              {otp}
            </span>
          </div>
          <p style="color: #777; font-size: 12px; text-align: center;">This OTP is valid for 10 minutes.</p>
        </div>
      </body>
    </html>
    """
    _send_email_smtp(receiver_email, subject, html_content, "Cloud Engine")

def send_reset_otp_email(receiver_email: str, username: str, otp: int):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    if not sender_email or not sender_password: return

    subject = "🔒 Password Reset Request - Cloud API"
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px; border-top: 5px solid #2196F3; box-shadow: 0px 4px 10px rgba(0,0,0,0.1);">
          <h2 style="color: #2196F3; text-align: center;">🔒 Password Reset Request</h2>
          <p style="color: #333; font-size: 16px;">Hello <b>{username}</b>,</p>
          <p style="color: #555; font-size: 15px;">We received a request to reset your password for your Cloud Engine account. Use the OTP below to set a new password:</p>
          <div style="text-align: center; margin: 30px 0;">
            <span style="font-size: 28px; font-weight: bold; background: #e3f2fd; color: #0d47a1; padding: 10px 20px; border-radius: 5px; letter-spacing: 5px;">
              {otp}
            </span>
          </div>
          <p style="color: #d32f2f; font-size: 13px; text-align: center;"><b>⚠️ If you didn't request this, please ignore this email. Your account is safe.</b></p>
        </div>
      </body>
    </html>
    """
    _send_email_smtp(receiver_email, subject, html_content, "Cloud Security")

def send_welcome_email(receiver_email: str, username: str):
    subject = "🎉 Welcome to NEX CLOUD!"
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #050505; color: white; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: #0a0a0a; padding: 30px; border-radius: 15px; border: 1px solid #3b82f6; box-shadow: 0px 0px 20px rgba(59,130,246,0.3);">
          <h2 style="color: #3b82f6; text-align: center;">Welcome to the Elite Cloud, {username}! 🚀</h2>
          <p style="font-size: 16px; color: #ddd;">Your account has been successfully created.</p>
          <p style="font-size: 15px; color: #bbb;">You can now deploy bots, host APIs, and manage your servers with zero downtime.</p>
          <div style="text-align: center; margin-top: 30px;">
             <a href="https://cluadwebsite.vercel.app/dashboard" style="background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold;">Go to Dashboard</a>
          </div>
        </div>
      </body>
    </html>
    """
    _send_email_smtp(receiver_email, subject, html_content, "NEX Cloud")

def send_login_alert(receiver_email: str, username: str, ip_address: str):
    location = "Unknown"
    try:
        ip_data = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=3).json()
        if ip_data.get("status") == "success":
            location = f"{ip_data.get('city')}, {ip_data.get('country')}"
    except:
        pass

    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = "🚨 New Login Detected - NEX CLOUD"
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px; border-top: 5px solid #f44336; box-shadow: 0px 4px 10px rgba(0,0,0,0.1);">
          <h3 style="color: #f44336; text-align: center;">Security Alert: New Login</h3>
          <p>Hello <b>{username}</b>,</p>
          <p>A successful login was just detected on your account.</p>
          <ul style="background: #eee; padding: 15px; border-radius: 5px; list-style-type: none;">
              <li><b>Time:</b> {time_now}</li>
              <li><b>IP Address:</b> {ip_address}</li>
              <li><b>Location:</b> {location}</li>
          </ul>
          <p style="color: #777; font-size: 13px;">If this wasn't you, please change your password immediately!</p>
        </div>
      </body>
    </html>
    """
    _send_email_smtp(receiver_email, subject, html_content, "Cloud Security")

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

# ==========================================
# 📥 PAYLOAD MODELS
# ==========================================
class RegisterPayload(BaseModel):
    username: str
    email: str 
    password: str
    captcha_token: str 

class VerifyOTPPayload(BaseModel):
    email: str
    otp: int

class LoginPayload(BaseModel):
    username: str # 🔥 Payload property is called username, but user can enter email too
    password: str
    captcha_token: str 

class ForgotPasswordPayload(BaseModel):
    username: str # Isme user username YA email dono daal sakta hai

class ResetPasswordPayload(BaseModel):
    username: str
    otp: int
    new_password: str

# ==========================================
# 🔍 CHECK USERNAME ENDPOINT (🔥 Smart Update)
# ==========================================
@router.get("/check-username")
async def check_username_availability(username: str):
    clean_user = username.lower().strip()
    
    # 1. Main Database mein check karo
    user = await get_user_by_username(clean_user)
    if user:
        return {"available": False}
        
    # 2. OTP Store mein check karo (Jo users OTP verification ke liye ruke hain)
    for data in TEMP_OTP_STORE.values():
        # Check karte hain ki value dictionary hai ya nahi (kyunki reset-password me OTP int hota hai)
        if isinstance(data, dict) and data.get("username") == clean_user:
            return {"available": False} 
            
    return {"available": True}

# ==========================================
# 1. REGISTER & SEND OTP
# ==========================================
@router.post("/register")
async def register_user(payload: RegisterPayload, background_tasks: BackgroundTasks):
    
    is_human = await verify_turnstile(payload.captcha_token)
    if not is_human:
        raise HTTPException(status_code=400, detail="Robot detection failed! Tu bot hai kya? 🤖")

    # 🛡️ Email Sanitize aur Strict @gmail.com check
    clean_email_address = sanitize_email(payload.email)

    if await get_user_by_username(payload.username.lower().strip()):
        raise HTTPException(status_code=400, detail="Username already taken!")
        
    if await get_user_by_email(clean_email_address):
        raise HTTPException(status_code=400, detail="Email already registered! Stop trying to create multiple accounts.")

    otp = random.randint(100000, 999999)
    
    TEMP_OTP_STORE[clean_email_address] = {
        "username": payload.username.lower().strip(),
        "password_hash": hash_password(payload.password),
        "otp": otp,
        "original_email": payload.email 
    }

    background_tasks.add_task(send_otp_email, payload.email, payload.username, otp)

    return {"status": "success", "message": "OTP has been sent to your email. Please verify to complete registration."}

# ==========================================
# 2. VERIFY OTP & CREATE ACCOUNT
# ==========================================
@router.post("/verify-otp")
async def verify_otp(payload: VerifyOTPPayload, background_tasks: BackgroundTasks):
    # 🔥 FIX: Try-Except hata diya! Agar email invalid hai, toh yahi 400 error de dega. Bypass impossible!
    clean_email_address = sanitize_email(payload.email)

    if clean_email_address not in TEMP_OTP_STORE:
        raise HTTPException(status_code=404, detail="No pending registration found for this email.")

    stored_data = TEMP_OTP_STORE[clean_email_address]

    if stored_data["otp"] != payload.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP! Please try again.")

    api_key = f"cloud_key_{hash_password(stored_data['username'] + str(random.random()))[:16]}"
    
    new_user = {
        "username": stored_data["username"],
        "email": clean_email_address,
        "password": stored_data["password_hash"],
        "api_key": api_key,
        "is_suspended": False,
        "is_premium": False
    }
    
    await create_user(new_user)
    
    background_tasks.add_task(send_welcome_email, clean_email_address, stored_data["username"])
    
    del TEMP_OTP_STORE[clean_email_address]

    return {"status": "success", "message": f"Account created successfully! Welcome {stored_data['username']} 🚀"}

# ==========================================
# 3. LOGIN ENDPOINT (🔥 Smart Logic for Username or Email)
# ==========================================
@router.post("/login")
async def login_user(payload: LoginPayload, request: Request, background_tasks: BackgroundTasks):

    is_human = await verify_turnstile(payload.captcha_token)
    if not is_human:
        raise HTTPException(status_code=400, detail="Robot detection failed! Tu bot hai kya? 🤖")

    # The payload.username could contain an email OR a username
    login_identifier = payload.username.lower().strip()

    if "@" in login_identifier:
        try:
            # Re-use our strict email sanitization (blocks dot tricks, ensures gmail etc.)
            clean_email = sanitize_email(login_identifier)
            user = await get_user_by_email(clean_email)
        except Exception:
             # If sanitize_email throws an error (e.g. not gmail), it's definitely not a valid user
             raise HTTPException(status_code=404, detail="Account not found! Please check your credentials.")
    else:
        user = await get_user_by_username(login_identifier)
    
    if not user:
        raise HTTPException(status_code=404, detail="Account not found! Please check your credentials.")

    provided_hash = hash_password(payload.password)

    if user["password"] != provided_hash:
        raise HTTPException(status_code=401, detail="Incorrect Password!")

    client_ip = request.client.host if request.client else "Unknown IP"
    background_tasks.add_task(send_login_alert, user["email"], user["username"], client_ip)

    return {
        "status": "success", 
        "message": "Login successful! Welcome back.", 
        "api_key": user["api_key"],
        "username": user["username"],
        "is_premium": user.get("is_premium", False),
        "is_suspended": user.get("is_suspended", False)
    }

# ==========================================
# 4. FORGOT PASSWORD (Supports Username OR Email)
# ==========================================
@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordPayload, background_tasks: BackgroundTasks):
    # 🔥 FIX: Smart Logic! Agar '@' hai toh Email mano, varna Username mano.
    if "@" in payload.username:
        try:
            clean_email = sanitize_email(payload.username)
            user = await get_user_by_email(clean_email)
        except Exception:
            raise HTTPException(status_code=404, detail="User or Email not found in our database!")
    else:
        user = await get_user_by_username(payload.username.lower().strip())
        
    if not user:
        raise HTTPException(status_code=404, detail="User or Email not found in our database!")

    actual_username = user["username"]
    user_email = user["email"]
    
    reset_otp = random.randint(100000, 999999)
    TEMP_OTP_STORE[f"reset_{actual_username}"] = reset_otp
    
    background_tasks.add_task(send_reset_otp_email, user_email, actual_username, reset_otp)

    return {"status": "success", "message": f"A password reset OTP has been sent to the registered email for {actual_username}."}

# ==========================================
# 5. VERIFY RESET OTP & CHANGE PASSWORD
# ==========================================
@router.post("/reset-password")
async def reset_password(payload: ResetPasswordPayload):
    # 🔥 FIX: Yahan bhi same Smart Logic taaki bypass na ho
    if "@" in payload.username:
        try:
            clean_email = sanitize_email(payload.username)
            user = await get_user_by_email(clean_email)
        except Exception:
             raise HTTPException(status_code=404, detail="User or Email not found!")
    else:
        user = await get_user_by_username(payload.username.lower().strip())
        
    if not user:
        raise HTTPException(status_code=404, detail="User or Email not found!")

    actual_username = user["username"]
    store_key = f"reset_{actual_username}"
    
    if store_key not in TEMP_OTP_STORE:
        raise HTTPException(status_code=400, detail="No pending password reset request found, or OTP expired!")

    if TEMP_OTP_STORE[store_key] != payload.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP! Please try again.")

    new_hash = hash_password(payload.new_password)
    
    await update_user_password(actual_username, new_hash)
    del TEMP_OTP_STORE[store_key]

    return {"status": "success", "message": "✅ Password has been reset successfully! You can now login with your new password."}
                            
