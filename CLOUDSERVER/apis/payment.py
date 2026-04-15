from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import httpx # 🚀 CHANGED: requests to httpx for async operation

from CLOUDSERVER.database.user import get_user_by_username, update_user_premium
from CLOUDSERVER.auth.verify import verify_api_key

router = APIRouter()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")

# ==========================================
# 📧 PREMIUM ACTIVATION EMAIL TEMPLATE
# ==========================================
def send_premium_success_email(receiver_email: str, username: str, duration_days: int):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    if not sender_email or not sender_password:
        print("🚨 Email credentials missing in .env")
        return

    subject = "👑 Welcome to NEX CLOUD Premium!"
    expiry_date = (datetime.now() + timedelta(days=duration_days)).strftime("%d %B, %Y")

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #050505; color: white; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: #0a0a0a; padding: 30px; border-radius: 15px; border: 1px solid #a855f7; box-shadow: 0px 0px 20px rgba(168,85,247,0.3);">
          <h2 style="color: #a855f7; text-align: center;">Payment Successful! 🚀</h2>
          <p style="font-size: 16px; color: #ddd;">Hello <b>{username}</b>,</p>
          <p style="font-size: 15px; color: #bbb;">Your transaction has been verified. Welcome to the elite tier of NEX CLOUD.</p>
          
          <div style="background: #111; padding: 15px; border-radius: 10px; margin: 20px 0; border: 1px dashed #555;">
            <p style="margin: 5px 0;">💎 <b>Plan:</b> {duration_days} Days Premium</p>
            <p style="margin: 5px 0;">⏳ <b>Valid Until:</b> {expiry_date}</p>
            <p style="margin: 5px 0;">⚡ <b>Features Unlocked:</b> Unlimited Deployments, Docker Support, Zero Wait Time.</p>
          </div>
          
          <p style="color: #888; font-size: 13px; text-align: center;">Thank you for supporting our Bhaichara ecosystem! ❤️</p>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"NEX Billing <{sender_email}>"
    msg["To"] = receiver_email
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"✅ Premium success email sent to {receiver_email}")
    except Exception as e:
        print(f"🚨 [EMAIL FAILED] {str(e)}")


# ==========================================
# 📥 PAYLOAD MODELS (Updated to match Frontend)
# ==========================================
class CouponPayload(BaseModel):
    code: str  # 🛠️ FIXED: Matched frontend key

class PaymentSubmitPayload(BaseModel):
    transaction_id: str # 🛠️ FIXED: Matched frontend key
    amount: float       # 🛠️ FIXED: Matched frontend key
    plan: str           # 🛠️ FIXED: Matched frontend key
    coupon_used: Optional[str] = None


# ==========================================
# 1. VERIFY COUPON API
# ==========================================
@router.post("/verify-coupon") # 🛠️ FIXED: Endpoint name matches frontend
async def verify_coupon(payload: CouponPayload, current_user: str = Depends(verify_api_key)):
    # 📝 Yahan DB se coupon check hoga (Dummy logic for now)
    # coupon = await get_coupon_by_code(payload.code)
    
    # Dummy Coupon Validation
    valid_coupons = {
        "NEXFREE": {"discount_percentage": 100},
        "BHAICHARA": {"discount_percentage": 50}
    }
    
    if payload.code.upper() in valid_coupons:
        return {
            "status": "success", 
            "discount_percentage": valid_coupons[payload.code.upper()]["discount_percentage"]
        }
    else:
        raise HTTPException(status_code=400, detail="❌ Invalid or Expired Coupon!")


# ==========================================
# 2. SUBMIT PAYMENT (To Telegram)
# ==========================================
@router.post("/submit-payment")
async def submit_payment(payload: PaymentSubmitPayload, current_user: str = Depends(verify_api_key)):
    
    # Helper to extract months from string like "NEX Premium 1 Month"
    plan_months = 1 # Default
    if "1" in payload.plan: plan_months = 1
    elif "6" in payload.plan: plan_months = 6
    elif "12" in payload.plan: plan_months = 12

    # 1. Prepare Message for Telegram Admin
    msg_text = (
        f"🚨 <b>NEW PAYMENT PENDING</b> 🚨\n\n"
        f"👤 <b>User:</b> <code>{current_user}</code>\n"
        f"💰 <b>Amount:</b> ₹{payload.amount}\n"
        f"📅 <b>Plan:</b> {payload.plan}\n"
        f"🎫 <b>Coupon:</b> {payload.coupon_used or 'None'}\n"
        f"🧾 <b>Txn ID:</b> <code>{payload.transaction_id}</code>\n\n"
        f"Approve or Reject this transaction?"
    )

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve|{current_user}|{plan_months}"},
                {"text": "❌ Reject", "callback_data": f"reject|{current_user}|{payload.transaction_id}"}
            ]
        ]
    }

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # 🚀 CHANGED: Using httpx instead of requests
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "chat_id": TELEGRAM_ADMIN_ID,
            "text": msg_text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        })

    if response.status_code == 200:
        return {"status": "success", "message": "✅ Payment details submitted for manual verification."}
    else:
        print(f"🚨 Telegram API Error: {response.text}")
        raise HTTPException(status_code=500, detail="Failed to notify admin. Check Bot Token.")


# ==========================================
# 3. TELEGRAM WEBHOOK (Admin Action)
# ==========================================
@router.post("/tg-webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    if "callback_query" in data:
        callback_id = data["callback_query"]["id"]
        chat_id = data["callback_query"]["message"]["chat"]["id"]
        message_id = data["callback_query"]["message"]["message_id"]
        callback_data = data["callback_query"]["data"] 
        
        if str(chat_id) != str(TELEGRAM_ADMIN_ID):
            return {"status": "unauthorized"}

        action, username, extra_data = callback_data.split("|")

        async with httpx.AsyncClient() as client:
            if action == "approve":
                plan_months = int(extra_data)
                duration_days = plan_months * 30
                
                # 1. Update Database
                await update_user_premium(username, is_premium=True, days=duration_days)
                
                # 2. Send Email
                user_info = await get_user_by_username(username)
                if user_info and "email" in user_info:
                    background_tasks.add_task(send_premium_success_email, user_info["email"], username, duration_days)

                # 3. Update TG Message
                await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"✅ Payment APPROVED for {username} ({plan_months} months).\nStatus updated in DB."
                })

            elif action == "reject":
                await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"❌ Payment REJECTED for {username} (Txn: {extra_data})."
                })

            # Answer callback
            await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", json={
                "callback_query_id": callback_id,
                "text": "Action Successful!"
            })

    return {"status": "ok"}
    
