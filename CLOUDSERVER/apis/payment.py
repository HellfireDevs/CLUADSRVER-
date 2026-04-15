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
# 🔥 FIX 1: Yahan payments_collection import add kiya hai
from CLOUDSERVER.database.database import tickets_collection, payments_collection 
from CLOUDSERVER.auth.verify import verify_api_key

# Transaction History
from CLOUDSERVER.database.deploys import get_user_transaction_history

router = APIRouter()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")

# ==========================================
# 📧 EMAIL HELPERS
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
    send_email_helper(receiver_email, "👑 Welcome to NEX CLOUD Premium!", html_content)


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
    
    plan_months = 1 
    if "1" in payload.plan: plan_months = 1
    elif "6" in payload.plan: plan_months = 6
    elif "12" in payload.plan: plan_months = 12

    # 🔥 FIX 2: Transaction ko DB mein 'Pending' status ke sath save karna zaroori hai
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

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
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
        raise HTTPException(status_code=500, detail="Failed to notify admin. Check Bot Token.")


# ==========================================
# 3. TELEGRAM WEBHOOK (Admin Action & Support Reply)
# ==========================================
@router.post("/tg-webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    # --- SCENARIO A: PAYMENT BUTTON CLICKED ---
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
                
                # 🔥 FIX 3: Approve hone pe DB me transaction 'Success' mark kardo
                await payments_collection.update_many(
                    {"username": username, "status": "Pending"},
                    {"$set": {"status": "Success"}}
                )

                await update_user_premium(username, is_premium=True, days=duration_days)
                
                user_info = await get_user_by_username(username)
                if user_info and "email" in user_info:
                    background_tasks.add_task(send_premium_success_email, user_info["email"], username, duration_days)

                await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"✅ Payment APPROVED for {username} ({plan_months} months).\nStatus updated in DB."
                })

            elif action == "reject":
                # 🔥 FIX 4: Reject hone pe DB me transaction 'Rejected' mark kardo
                await payments_collection.update_many(
                    {"username": username, "utr_number": extra_data, "status": "Pending"},
                    {"$set": {"status": "Rejected"}}
                )

                await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText", json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"❌ Payment REJECTED for {username} (Txn: {extra_data})."
                })

            await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", json={
                "callback_query_id": callback_id,
                "text": "Action Successful!"
            })

    # --- SCENARIO B: ADMIN REPLIES TO A SUPPORT TICKET ---
    if "message" in data and "reply_to_message" in data["message"]:
        admin_reply = data["message"].get("text", "")
        reply_to_id = data["message"]["reply_to_message"]["message_id"]
        chat_id = data["message"]["chat"]["id"]
        
        if str(chat_id) == str(TELEGRAM_ADMIN_ID) and admin_reply:
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
                    await client.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={
                        "chat_id": TELEGRAM_ADMIN_ID,
                        "text": f"✅ Reply sent to {username} for Ticket {ticket_id}!",
                        "reply_to_message_id": data["message"]["message_id"]
                    })

    return {"status": "ok"}


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
                    
