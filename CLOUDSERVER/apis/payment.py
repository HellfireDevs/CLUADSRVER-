from fastapi import APIRouter, BackgroundTasks, Header, Request, HTTPException, Depends
from pydantic import BaseModel
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# 🚀 Apne DB imports yahan add kar lena
from CLOUDSERVER.database.user import get_user_by_username, update_user_premium
# from CLOUDSERVER.database.payments import save_transaction, get_transaction, get_coupon_by_code
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
    except Exception as e:
        print(f"🚨 [EMAIL FAILED] {str(e)}")


# ==========================================
# 📥 PAYLOAD MODELS
# ==========================================
class CouponPayload(BaseModel):
    coupon_code: str

class PaymentSubmitPayload(BaseModel):
    txn_id: str
    amount_paid: float
    plan_months: int
    coupon_used: str = None


# ==========================================
# 1. CHECK COUPON API (Frontend use karega)
# ==========================================
@router.post("/apply-coupon")
async def apply_coupon(payload: CouponPayload, current_user: str = Depends(verify_api_key)):
    # 📝 Yahan DB se coupon check hoga (Dummy logic for now)
    # coupon = await get_coupon_by_code(payload.coupon_code)
    coupon = {"code": "FREE1MONTH", "type": "free_months", "value": 1} # Ye DB se aayega
    
    if not coupon:
        raise HTTPException(status_code=400, detail="❌ Invalid or Expired Coupon!")

    if coupon["type"] == "free_months":
        return {"status": "success", "message": f"🎉 100% OFF applied! {coupon['value']} Month(s) Free.", "discount_type": "free", "value": coupon["value"]}
    elif coupon["type"] == "discount":
        return {"status": "success", "message": f"🎉 {coupon['value']}% OFF applied!", "discount_type": "percent", "value": coupon["value"]}


# ==========================================
# 2. SUBMIT PAYMENT (Telegram Approval ke liye bhejna)
# ==========================================
@router.post("/submit-payment")
async def submit_payment(payload: PaymentSubmitPayload, current_user: str = Depends(verify_api_key)):
    # 1. DB mein Transaction "Pending" save karna
    txn_ref = f"TXN_{payload.txn_id[:6].upper()}_{current_user}"
    # await save_transaction({"txn_id": payload.txn_id, "user": current_user, "amount": payload.amount_paid, "status": "pending"})

    # 2. Telegram Bot ke through tujhe (Admin) message bhejna
    msg_text = (
        f"🚨 <b>NEW PAYMENT RECEIVED</b> 🚨\n\n"
        f"👤 <b>User:</b> {current_user}\n"
        f"💰 <b>Amount:</b> ₹{payload.amount_paid}\n"
        f"📅 <b>Plan:</b> {payload.plan_months} Month(s)\n"
        f"🎫 <b>Coupon:</b> {payload.coupon_used or 'None'}\n"
        f"🧾 <b>Txn ID:</b> <code>{payload.txn_id}</code>\n\n"
        f"Approve or Reject this transaction:"
    )

    # Telegram Inline Keyboard Buttons (Callback data mein txn_ref aur username bhej rahe hain)
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve|{current_user}|{payload.plan_months}"},
                {"text": "❌ Reject", "callback_data": f"reject|{current_user}|{payload.txn_id}"}
            ]
        ]
    }

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={
        "chat_id": TELEGRAM_ADMIN_ID,
        "text": msg_text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    })

    if response.status_code == 200:
        return {"status": "success", "message": "✅ Payment details submitted. Please wait 1-2 hours for manual verification."}
    else:
        raise HTTPException(status_code=500, detail="Failed to notify admin. Contact support.")


# ==========================================
# 3. TELEGRAM WEBHOOK (Jab Admin Confirm/Reject dabayega)
# ==========================================
# 👉 Telegram Bot ko iss URL pe set karna hoga: https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://tera-backend.com/api/tg-webhook
@router.post("/tg-webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    # Check if this is a button click (Callback Query)
    if "callback_query" in data:
        callback_id = data["callback_query"]["id"]
        chat_id = data["callback_query"]["message"]["chat"]["id"]
        message_id = data["callback_query"]["message"]["message_id"]
        callback_data = data["callback_query"]["data"] # "approve|username|months"
        
        # Security check: Make sure only you (Admin) pressed it
        if str(chat_id) != str(TELEGRAM_ADMIN_ID):
            return {"status": "unauthorized"}

        action, username, extra_data = callback_data.split("|")

        if action == "approve":
            plan_months = int(extra_data)
            duration_days = plan_months * 30
            
            # 1. DB mein user ko premium do aur dates set karo
            # await update_user_premium(username, is_premium=True, days=duration_days)
            
            # 2. User ko success email bhejo (Background mein)
            user_info = await get_user_by_username(username)
            if user_info and "email" in user_info:
                background_tasks.add_task(send_premium_success_email, user_info["email"], username, duration_days)

            # 3. Telegram message update kardo taaki buttons hat jayein
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": f"✅ Payment APPROVED for {username} ({plan_months} months)."
            })

        elif action == "reject":
            # Database mein Txn status Rejected kar do
            # ...
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": f"❌ Payment REJECTED for {username} (Txn: {extra_data})."
            })

        # Telegram ko popup hatane ke liye answer bhejna zaroori hai
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": callback_id,
            "text": "Action Successful!"
        })

    return {"status": "ok"}

