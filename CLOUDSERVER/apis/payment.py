from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import httpx 

from CLOUDSERVER.database.user import get_user_by_username, update_user_premium
from CLOUDSERVER.database.database import tickets_collection, payments_collection, users_collection # 🔥 FIX: users_collection added
from CLOUDSERVER.auth.verify import verify_api_key

# Transaction History
from CLOUDSERVER.database.deploys import get_user_transaction_history

router = APIRouter()

# 🔥 GLOBAL TOKEN HATA DIYA: Functions ke andar call karenge taaki .env proper load ho
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")

# ==========================================
# 📧 EMAIL HELPERS (Approve & Reject Both)
# ==========================================
def send_email_helper(receiver_email: str, subject: str, html_content: str):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    if not sender_email or not sender_password: return
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"NEX Cloud <{sender_email}>"
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

def send_premium_success_email(receiver_email: str, username: str, duration_days: int):
    expiry_date = (datetime.now() + timedelta(days=duration_days)).strftime("%d %B, %Y")
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #050505; color: white; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: #0a0a0a; padding: 30px; border-radius: 15px; border: 1px solid #4CAF50; box-shadow: 0px 0px 20px rgba(76,175,80,0.3);">
          <h2 style="color: #4CAF50; text-align: center;">Payment Successful! 🚀</h2>
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
    send_email_helper(receiver_email, "👑 Welcome to NEX CLOUD Premium!", html_content)

# 🔥 NAYA: Reject Email Template
def send_premium_reject_email(receiver_email: str, username: str, transaction_id: str):
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #050505; color: white; padding: 20px;">
        <div style="max-width: 500px; margin: auto; background: #0a0a0a; padding: 30px; border-radius: 15px; border: 1px solid #f44336; box-shadow: 0px 0px 20px rgba(244,67,54,0.3);">
          <h2 style="color: #f44336; text-align: center;">Payment Rejected ❌</h2>
          <p style="font-size: 16px; color: #ddd;">Hello <b>{username}</b>,</p>
          <p style="font-size: 15px; color: #bbb;">We could not verify your recent payment. Your transaction has been marked as failed.</p>
          
          <div style="background: #111; padding: 15px; border-radius: 10px; margin: 20px 0; border: 1px dashed #555;">
            <p style="margin: 5px 0;">🧾 <b>Transaction ID:</b> {transaction_id}</p>
            <p style="margin: 5px 0; color: #f44336;">⚠️ <b>Reason:</b> Invalid UTR or Payment not received.</p>
          </div>
          
          <p style="font-size: 14px; color: #bbb;">If you think this is a mistake, please open a Support Ticket from your dashboard with the screenshot of your payment.</p>
          <p style="color: #888; font-size: 13px; text-align: center;">NEX CLOUD Support Team</p>
        </div>
      </body>
    </html>
    """
    send_email_helper(receiver_email, "❌ Payment Verification Failed", html_content)


# ==========================================
# 📥 PAYLOAD MODELS 
# ==========================================
class CouponPayload(BaseModel):
    code: str  

class PaymentSubmitPayload(BaseModel):
    transaction_id: str 
    amount: float       
    plan: str           
    coupon_used: Optional[str] = None


# ==========================================
# 1. VERIFY COUPON API
# ==========================================
@router.post("/verify-coupon") 
async def verify_coupon(payload: CouponPayload, current_user: str = Depends(verify_api_key)):
    valid_coupons = {
        "NEXFREE": {"discount_percentage": 100},
        "BHAICHARA": {"discount_percentage": 50},
        "TANNU@1289": {"discount_percentage": 100}
    }
    
    if payload.code.upper() in valid_coupons:
        return {
            "status": "success", 
            "discount_percentage": valid_coupons[payload.code.upper()]["discount_percentage"]
        }
    else:
        raise HTTPException(status_code=400, detail="❌ Invalid or Expired Coupon!")


# ==========================================
# 2. SUBMIT PAYMENT (To Telegram & DB)
# ==========================================
@router.post("/submit-payment")
async def submit_payment(payload: PaymentSubmitPayload, current_user: str = Depends(verify_api_key)):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    admin_id = os.getenv("TELEGRAM_ADMIN_ID")
    
    plan_months = 1 
    if "1" in payload.plan: plan_months = 1
    elif "6" in payload.plan: plan_months = 6
    elif "12" in payload.plan: plan_months = 12

    txn_data = {
        "username": current_user,
        "amount": payload.amount,
        "plan": payload.plan,
        "utr_number": payload.transaction_id,
        "coupon_code": payload.coupon_used,
        "status": "Pending",
        "timestamp": datetime.utcnow()
    }
    await payments_collection.insert_one(txn_data)

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

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "chat_id": admin_id,
            "text": msg_text,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        })

    if response.status_code == 200:
        return {"status": "success", "message": "✅ Payment details submitted for manual verification."}
    else:
        raise HTTPException(status_code=500, detail="Failed to notify admin. Check Bot Token.")


# ==========================================
# 3. THE MASTER TELEGRAM WEBHOOK 🔥 (Merge VIP & Payments)
# ==========================================
@router.post("/tg-webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    admin_id = os.getenv("TELEGRAM_ADMIN_ID")
    
    try:
        data = await request.json()
        
        # --- SCENARIO A: ANY INLINE BUTTON CLICKED ---
        if "callback_query" in data:
            callback_id = data["callback_query"]["id"]
            chat_id = data["callback_query"]["message"]["chat"]["id"]
            message_id = data["callback_query"]["message"]["message_id"]
            callback_data = data["callback_query"]["data"] 
            
            if str(chat_id) != str(admin_id):
                return {"status": "unauthorized"}

            # 🟢 VIP ACCESS BUTTONS LOGIC (From support.py)
            if callback_data.startswith("vip_approve_") or callback_data.startswith("vip_reject_"):
                async with httpx.AsyncClient() as client:
                    if callback_data.startswith("vip_approve_"):
                        username = callback_data.replace("vip_approve_", "")
                        await users_collection.update_one({"username": username}, {"$set": {"pm2_access": True}})
                        
                        await client.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": f"✅ <b>VIP Access Approved for:</b> <code>{username}</code>\nAb wo bindass PM2 use kar sakta hai!",
                            "parse_mode": "HTML"
                        })
                    else:
                        username = callback_data.replace("vip_reject_", "")
                        await client.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": f"❌ <b>VIP Access Rejected for:</b> <code>{username}</code>",
                            "parse_mode": "HTML"
                        })
                        
                    await client.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={
                        "callback_query_id": callback_id, "text": "Action Done!"
                    })
                return {"status": "ok"}


            # 🔵 PAYMENT BUTTONS LOGIC
            if "|" in callback_data:
                action, username, extra_data = callback_data.split("|")

                async with httpx.AsyncClient() as client:
                    if action == "approve":
                        plan_months = int(extra_data)
                        duration_days = plan_months * 30
                        
                        await payments_collection.update_many(
                            {"username": username, "status": "Pending"},
                            {"$set": {"status": "Success"}}
                        )
                        await update_user_premium(username, is_premium=True, days=duration_days)
                        
                        # Email Bhejo
                        user_info = await get_user_by_username(username)
                        if user_info and "email" in user_info:
                            background_tasks.add_task(send_premium_success_email, user_info["email"], username, duration_days)

                        await client.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": f"✅ Payment APPROVED for {username} ({plan_months} months).\nStatus updated in DB."
                        })

                    elif action == "reject":
                        await payments_collection.update_many(
                            {"username": username, "utr_number": extra_data, "status": "Pending"},
                            {"$set": {"status": "Rejected"}}
                        )
                        
                        # Reject Email Bhejo
                        user_info = await get_user_by_username(username)
                        if user_info and "email" in user_info:
                            background_tasks.add_task(send_premium_reject_email, user_info["email"], username, extra_data)

                        await client.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={
                            "chat_id": chat_id, "message_id": message_id,
                            "text": f"❌ Payment REJECTED for {username} (Txn: {extra_data})."
                        })

                    await client.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={
                        "callback_query_id": callback_id, "text": "Payment Action Done!"
                    })
                return {"status": "ok"}

        # --- SCENARIO B: ADMIN REPLIES TO A SUPPORT TICKET ---
        if "message" in data and "reply_to_message" in data["message"]:
            admin_reply = data["message"].get("text", "")
            reply_to_id = data["message"]["reply_to_message"]["message_id"]
            chat_id = data["message"]["chat"]["id"]
            
            if str(chat_id) == str(admin_id) and admin_reply:
                ticket = await tickets_collection.find_one({"tg_message_id": reply_to_id})
                
                if ticket:
                    await tickets_collection.update_one(
                        {"_id": ticket["_id"]},
                        {"$set": {"status": "Answered", "admin_reply": admin_reply}}
                    )
                    
                    username = ticket["owner"]
                    ticket_id = ticket["ticket_id"]
                    
                    user_info = await get_user_by_username(username)
                    if user_info and "email" in user_info:
                        frontend_url = "https://cluadwebsite.vercel.app/support"
                        html_content = f"""
                        <div style="font-family: Arial; background: #050505; color: white; padding: 20px;">
                            <div style="max-width: 500px; margin: auto; background: #0a0a0a; padding: 30px; border-radius: 15px; border-top: 4px solid #a855f7;">
                                <h2 style="color: #a855f7;">Support Ticket Updated 🎫</h2>
                                <p>Hello <b>{username}</b>,</p>
                                <p>An admin has replied to your ticket (<b>{ticket_id}</b>):</p>
                                <div style="background: #111; padding: 15px; border-left: 3px solid #a855f7; margin: 20px 0; font-style: italic;">
                                    "{admin_reply}"
                                </div>
                                <a href="{frontend_url}" style="display: inline-block; padding: 12px 24px; background: #a855f7; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 10px;">
                                    View Ticket on Dashboard
                                </a>
                            </div>
                        </div>
                        """
                        background_tasks.add_task(send_email_helper, user_info["email"], f"Update on Ticket {ticket_id}", html_content)
                    
                    async with httpx.AsyncClient() as client:
                        await client.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={
                            "chat_id": admin_id,
                            "text": f"✅ Reply sent to {username} for Ticket {ticket_id}!",
                            "reply_to_message_id": data["message"]["message_id"]
                        })

        return {"status": "ok"}
    except Exception as e:
        print(f"🚨 Webhook Master Error: {e}")
        return {"status": "error"}


# ==========================================
# 4. 💸 GET TRANSACTION HISTORY
# ==========================================
@router.get("/transaction-history")
async def transaction_history(current_user: str = Depends(verify_api_key)):
    """
    User apne API key se request bhejega aur ye usko uski saari history de dega.
    """
    try:
        history = await get_user_transaction_history(current_user)
        
        if not history:
            return {
                "status": "success",
                "message": "No transactions found.",
                "transactions": []
            }
            
        return {
            "status": "success",
            "message": "Transaction history fetched successfully.",
            "total_transactions": len(history),
            "transactions": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")
                    
