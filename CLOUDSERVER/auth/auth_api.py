from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import json
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# ==========================================
# 🧠 DATABASE & TEMP STORAGE SETUP
# ==========================================
USERS_DB_FILE = "users_db.json"
TEMP_OTP_STORE = {} # Jab tak OTP verify nahi hota, data yahan rahega

def load_users():
    if not os.path.exists(USERS_DB_FILE):
        return {}
    with open(USERS_DB_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Password Hashing (Taaki DB mein password safe rahe)
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# 📧 MAST EMAIL TEMPLATE ENGINE
# ==========================================
def send_otp_email(receiver_email: str, username: str, otp: int):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    if not sender_email or not sender_password:
        print("🚨 [EMAIL ERROR] .env mein SENDER_EMAIL ya SENDER_PASSWORD nahi mila!")
        return

    subject = "☁️ Verify Your Cloud API Account ☁️"
    
    # HTML Email Template (Mast wala)
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
          <p style="color: #777; font-size: 12px; text-align: center;">This OTP is valid for 10 minutes. Please do not share it with anyone.</p>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Cloud Engine <{sender_email}>"
    msg["To"] = receiver_email
    msg.attach(MIMEText(html_content, "html"))

    try:
        # Gmail SMTP Server connect karna
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"📧 [EMAIL SENT] OTP successfully sent to {receiver_email}")
    except Exception as e:
        print(f"🚨 [EMAIL FAILED] {str(e)}")

# ==========================================
# 📥 PAYLOAD MODELS (Frontend se kya aayega)
# ==========================================
class RegisterPayload(BaseModel):
    username: str
    email: EmailStr
    password: str

class VerifyOTPPayload(BaseModel):
    email: EmailStr
    otp: int

class LoginPayload(BaseModel):
    username: str
    password: str

class ForgotPasswordPayload(BaseModel):
    username: str

# ==========================================
# 1. REGISTER & SEND OTP ENDPOINT
# ==========================================
@router.post("/register")
async def register_user(payload: RegisterPayload, background_tasks: BackgroundTasks):
    users = load_users()
    
    # Check if username or email already exists
    if payload.username in users:
        raise HTTPException(status_code=400, detail="Username already taken!")
    for user_data in users.values():
        if user_data["email"] == payload.email:
            raise HTTPException(status_code=400, detail="Email already registered!")

    # Generate 6-digit Random OTP
    otp = random.randint(100000, 999999)
    
    # Store temporarily
    TEMP_OTP_STORE[payload.email] = {
        "username": payload.username,
        "password_hash": hash_password(payload.password),
        "otp": otp
    }

    # Background mein mast sa email bhej do
    background_tasks.add_task(send_otp_email, payload.email, payload.username, otp)

    return {
        "status": "success", 
        "message": "OTP has been sent to your email. Please verify to complete registration."
    }

# ==========================================
# 2. VERIFY OTP & CREATE ACCOUNT
# ==========================================
@router.post("/verify-otp")
async def verify_otp(payload: VerifyOTPPayload):
    if payload.email not in TEMP_OTP_STORE:
        raise HTTPException(status_code=404, detail="No pending registration found for this email.")

    stored_data = TEMP_OTP_STORE[payload.email]

    if stored_data["otp"] != payload.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP! Please try again.")

    # OTP Sahi hai! Ab Account JSON mein save kar do
    users = load_users()
    users[stored_data["username"]] = {
        "email": payload.email,
        "password": stored_data["password_hash"],
        "api_key": f"cloud_key_{hash_password(stored_data['username'] + str(random.random()))[:16]}" # Fake API Key assign ki
    }
    save_users(users)
    
    # Temp memory se delete kar do
    del TEMP_OTP_STORE[payload.email]

    return {
        "status": "success", 
        "message": f"Account created successfully! Welcome {stored_data['username']} 🚀"
    }

# ==========================================
# 3. LOGIN ENDPOINT
# ==========================================
@router.post("/login")
async def login_user(payload: LoginPayload):
    users = load_users()
    
    if payload.username not in users:
        raise HTTPException(status_code=404, detail="Username not found!")

    stored_hash = users[payload.username]["password"]
    provided_hash = hash_password(payload.password)

    if stored_hash != provided_hash:
        raise HTTPException(status_code=401, detail="Incorrect Password!")

    return {
        "status": "success",
        "message": "Login successful! Welcome back.",
        "api_key": users[payload.username]["api_key"]
    }

# ==========================================
# 4. FORGOT PASSWORD (Basic Endpoint setup)
# ==========================================
@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordPayload, background_tasks: BackgroundTasks):
    users = load_users()
    
    if payload.username not in users:
        raise HTTPException(status_code=404, detail="Username not found!")

    user_email = users[payload.username]["email"]
    
    # Naya reset OTP generate karna
    reset_otp = random.randint(100000, 999999)
    TEMP_OTP_STORE[f"reset_{payload.username}"] = reset_otp
    
    # Background email task
    background_tasks.add_task(send_otp_email, user_email, payload.username, reset_otp)

    return {
        "status": "success",
        "message": f"A password reset OTP has been sent to the registered email for {payload.username}."
  }
  
