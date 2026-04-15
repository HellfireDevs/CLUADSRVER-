from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import os
import hashlib
from dotenv import load_dotenv

# 🚀 Naya MongoDB Import!
from CLOUDSERVER.database.user import create_user, get_user_by_username, get_user_by_email

load_dotenv()

router = APIRouter()

# ==========================================
# 🧠 TEMP STORAGE SETUP (For OTP)
# ==========================================
TEMP_OTP_STORE = {} # Jab tak OTP verify nahi hota, data memory mein rahega

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
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"📧 [EMAIL SENT] OTP successfully sent to {receiver_email}")
    except Exception as e:
        print(f"🚨 [EMAIL FAILED] {str(e)}")

# ==========================================
# 📥 PAYLOAD MODELS
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
    # MongoDB DB Checks
    if await get_user_by_username(payload.username):
        raise HTTPException(status_code=400, detail="Username already taken!")
        
    if await get_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email already registered!")

    # Generate 6-digit Random OTP
    otp = random.randint(100000, 999999)
    
    # Store temporarily
    TEMP_OTP_STORE[payload.email] = {
        "username": payload.username,
        "password_hash": hash_password(payload.password),
        "otp": otp
    }

    # Send email in background
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

    # Generate Secure API Key
    api_key = f"cloud_key_{hash_password(stored_data['username'] + str(random.random()))[:16]}"
    
    # User object for MongoDB
    new_user = {
        "username": stored_data["username"],
        "email": payload.email,
        "password": stored_data["password_hash"],
        "api_key": api_key
    }
    
    # Save User to MongoDB
    await create_user(new_user)
    
    # Clear temp memory
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
    user = await get_user_by_username(payload.username)
    
    if not user:
        raise HTTPException(status_code=404, detail="Username not found!")

    provided_hash = hash_password(payload.password)

    if user["password"] != provided_hash:
        raise HTTPException(status_code=401, detail="Incorrect Password!")

    return {
        "status": "success",
        "message": "Login successful! Welcome back.",
        "api_key": user["api_key"]
    }

# ==========================================
# 4. FORGOT PASSWORD (Basic Endpoint setup)
# ==========================================
@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordPayload, background_tasks: BackgroundTasks):
    user = await get_user_by_username(payload.username)
    
    if not user:
        raise HTTPException(status_code=404, detail="Username not found!")

    user_email = user["email"]
    
    reset_otp = random.randint(100000, 999999)
    TEMP_OTP_STORE[f"reset_{payload.username}"] = reset_otp
    
    background_tasks.add_task(send_otp_email, user_email, payload.username, reset_otp)

    return {
        "status": "success",
        "message": f"A password reset OTP has been sent to the registered email for {payload.username}."
    }
    
