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

# 🛑 Blocked Temp Mail Domains
BLOCKED_DOMAINS = {
    "mailinator.com", "10minutemail.com", "tempmail.com", "temp-mail.org", 
    "guerrillamail.com", "yopmail.com", "throwawaymail.com", "dispostable.com", 
    "getairmail.com", "trashmail.com", "sharklasers.com", "nada.ltd"
}

# 🛡️ Smart Email Normalizer (Dot/Plus trick killer)
def sanitize_email(email: str) -> str:
    email = email.lower().strip()
    username, domain = email.split('@')

    # Agar temp mail hai toh block karo
    if domain in BLOCKED_DOMAINS:
        raise HTTPException(status_code=400, detail="❌ Disposable/Temp emails are not allowed! Asli email use kar bhai.")

    # Gmail Dot aur Plus trick fixer
    if domain in ["gmail.com", "googlemail.com"]:
        # '+' ke baad ka sab kuch uda do
        username = username.split('+')[0]
        # Saare '.' (dots) uda do
        username = username.replace('.', '')
        # googlemail ko bhi gmail maan lo
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
    # Agar secret key nahi hai (testing time), toh pass hone do warna sab atak jayega
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
    """Naya Account banne par Congratulations mail"""
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
    """Naya login hone par security alert with IP & Location"""
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
    """Smtplib Helper function taaki code repeat na ho"""
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
    captcha_token: str # 🛡️ NEW: Captcha token from frontend

class VerifyOTPPayload(BaseModel):
    email: str
    otp: int

class LoginPayload(BaseModel):
    username: str
    password: str
    captcha_token: str # 🛡️ NEW: Login mein bhi Captcha token aayega

class ForgotPasswordPayload(BaseModel):
    username: str

class ResetPasswordPayload(BaseModel):
    username: str
    otp: int
    new_password: str

# ==========================================
# 1. REGISTER & SEND OTP (With Turnstile Lock)
# ==========================================
@router.post("/register")
async def register_user(payload: RegisterPayload, background_tasks: BackgroundTasks):
    
    # 🤖 Step 0: VERIFY CAPTCHA FIRST!
    is_human = await verify_turnstile(payload.captcha_token)
    if not is_human:
        raise HTTPException(status_code=400, detail="Robot detection failed! Tu bot hai kya? 🤖")

    # 🛡️ Step 1: Clean the email (removes dots, blocks temp mails)
    clean_email_address = sanitize_email(payload.email)

    if await get_user_by_username(payload.username):
        raise HTTPException(status_code=400, detail="Username already taken!")
        
    if await get_user_by_email(clean_email_address):
        raise HTTPException(status_code=400, detail="Email already registered! Stop trying to create multiple accounts.")

    otp = random.randint(100000, 999999)
    
    # Store with CLEAN email
    TEMP_OTP_STORE[clean_email_address] = {
        "username": payload.username,
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
    clean_email_address = sanitize_email(payload.email)

    if clean_email_address not in TEMP_OTP_STORE:
        raise HTTPException(status_code=404, detail="No pending registration found for this email.")

    stored_data = TEMP_OTP_STORE[clean_email_address]

    if stored_data["otp"] != payload.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP! Please try again.")

    api_key = f"cloud_key_{hash_password(stored_data['username'] + str(random.random()))[:16]}"
    
    new_user = {
        "username": stored_data["username"],
        "email": clean_email_address, # DB mein saaf wali email jayegi
        "password": stored_data["password_hash"],
        "api_key": api_key
    }
    
    await create_user(new_user)
    
    # 🎉 SUCCESS: Welcome Email Background mein bhej do
    background_tasks.add_task(send_welcome_email, clean_email_address, stored_data["username"])
    
    del TEMP_OTP_STORE[clean_email_address]

    return {"status": "success", "message": f"Account created successfully! Welcome {stored_data['username']} 🚀"}

# ==========================================
# 3. LOGIN ENDPOINT (With Turnstile Lock & Alert)
# ==========================================
@router.post("/login")
async def login_user(payload: LoginPayload, request: Request, background_tasks: BackgroundTasks):

    # 🤖 Step 0: VERIFY CAPTCHA FIRST!
    is_human = await verify_turnstile(payload.captcha_token)
    if not is_human:
        raise HTTPException(status_code=400, detail="Robot detection failed! Tu bot hai kya? 🤖")

    user = await get_user_by_username(payload.username)
    
    if not user:
        raise HTTPException(status_code=404, detail="Username not found!")

    provided_hash = hash_password(payload.password)

    if user["password"] != provided_hash:
        raise HTTPException(status_code=401, detail="Incorrect Password!")

    # 🚨 SECURITY ALERT: Login detect hua, email bhej do
    client_ip = request.client.host if request.client else "Unknown IP"
    background_tasks.add_task(send_login_alert, user["email"], payload.username, client_ip)

    return {"status": "success", "message": "Login successful! Welcome back.", "api_key": user["api_key"]}

# ==========================================
# 4. FORGOT PASSWORD
# ==========================================
@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordPayload, background_tasks: BackgroundTasks):
    user = await get_user_by_username(payload.username)
    
    if not user:
        raise HTTPException(status_code=404, detail="Username not found!")

    user_email = user["email"]
    reset_otp = random.randint(100000, 999999)
    TEMP_OTP_STORE[f"reset_{payload.username}"] = reset_otp
    
    background_tasks.add_task(send_reset_otp_email, user_email, payload.username, reset_otp)

    return {"status": "success", "message": f"A password reset OTP has been sent to the registered email for {payload.username}."}

# ==========================================
# 5. VERIFY RESET OTP & CHANGE PASSWORD
# ==========================================
@router.post("/reset-password")
async def reset_password(payload: ResetPasswordPayload):
    store_key = f"reset_{payload.username}"
    
    if store_key not in TEMP_OTP_STORE:
        raise HTTPException(status_code=400, detail="No pending password reset request found, or OTP expired!")

    if TEMP_OTP_STORE[store_key] != payload.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP! Please try again.")

    new_hash = hash_password(payload.new_password)
    
    await update_user_password(payload.username, new_hash)
    del TEMP_OTP_STORE[store_key]

    return {"status": "success", "message": "✅ Password has been reset successfully! You can now login with your new password."}
    
