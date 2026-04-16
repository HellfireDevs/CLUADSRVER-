import os
import random
import string
from datetime import datetime
import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request

from CLOUDSERVER.database.database import tickets_collection, users_collection
from CLOUDSERVER.auth.verify import verify_api_key

router = APIRouter()

def generate_ticket_id():
    return "TKT-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ==========================================
# 🔥 VIP PM2 TELEGRAM ALERT (With Buttons!)
# ==========================================
async def send_vip_access_request_tg(username: str, app_name: str):
    """Deploy.py se call hoga jab koi bina permission VIP engine use karega"""
    # 🔥 FIX: Token ab function ke andar fetch hoga taaki khali (None) na rahe!
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    admin_id = os.getenv("TELEGRAM_ADMIN_ID")
    
    if not bot_token or not admin_id:
        print("⚠️ Telegram Token ya TELEGRAM_ADMIN_ID set nahi hai .env mein!")
        return
    
    msg_text = (
        f"🚨 <b>VIP PM2 Access Request</b> 🚨\n\n"
        f"👤 <b>User:</b> <code>{username}</code>\n"
        f"🤖 <b>App Name:</b> <code>{app_name}</code>\n\n"
        f"⚠️ <i>User is trying to deploy using the VIP PM2 Engine but doesn't have access.</i>"
    )
    
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve VIP", "callback_data": f"vip_approve_{username}"},
                {"text": "❌ Reject", "callback_data": f"vip_reject_{username}"}
            ]
        ]
    }
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    json_payload = {
        "chat_id": admin_id, 
        "text": msg_text, 
        "parse_mode": "HTML",
        "reply_markup": reply_markup 
    }
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=json_payload)
            print(f"✅ VIP Request with Buttons sent to Admin for {username}")
        except Exception as e:
            print(f"🚨 Telegram Msg Failed: {e}")

# ==========================================
# 🤖 TELEGRAM WEBHOOK (For Handling Button Clicks)
# ==========================================
@router.post("/tg-webhook")
async def telegram_webhook(request: Request):
    """Jab tu Telegram pe Approve/Reject dabayega toh Telegram is endpoint pe data bhejega"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    try:
        update = await request.json()
        
        if "callback_query" in update:
            callback_query = update["callback_query"]
            callback_data = callback_query.get("data", "")
            message = callback_query.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            message_id = message.get("message_id")

            # ✅ Agar tu APPROVE dabata hai
            if callback_data.startswith("vip_approve_"):
                username = callback_data.replace("vip_approve_", "")
                
                # 1. Database mein VIP access ON kar do
                await users_collection.update_one({"username": username}, {"$set": {"pm2_access": True}})
                
                # 2. Telegram message ko edit karke 'Approved' likh do
                url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
                payload = {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"✅ <b>VIP Access Approved for:</b> <code>{username}</code>\nAb wo bindass PM2 use kar sakta hai!",
                    "parse_mode": "HTML"
                }
                async with httpx.AsyncClient() as client:
                    await client.post(url, json=payload)

            # ❌ Agar tu REJECT dabata hai
            elif callback_data.startswith("vip_reject_"):
                username = callback_data.replace("vip_reject_", "")
                
                url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
                payload = {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": f"❌ <b>VIP Access Rejected for:</b> <code>{username}</code>",
                    "parse_mode": "HTML"
                }
                async with httpx.AsyncClient() as client:
                    await client.post(url, json=payload)
                    
        return {"status": "ok"}
    except Exception as e:
        print(f"🚨 Webhook Error: {e}")
        return {"status": "error"}

# ==========================================
# 1. CREATE SUPPORT TICKET (With Screenshot)
# ==========================================
@router.post("/create")
async def create_ticket(
    subject: str = Form(...),
    message: str = Form(...),
    screenshot: UploadFile = File(None),
    current_user: str = Depends(verify_api_key)
):
    # 🔥 FIX: Token function ke andar fetch hoga
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    admin_id = os.getenv("TELEGRAM_ADMIN_ID")

    ticket_id = generate_ticket_id()
    
    msg_text = (
        f"🎫 <b>NEW SUPPORT TICKET</b> 🎫\n\n"
        f"👤 <b>User:</b> <code>{current_user}</code>\n"
        f"🔖 <b>Ticket ID:</b> <code>{ticket_id}</code>\n"
        f"📌 <b>Subject:</b> {subject}\n\n"
        f"📝 <b>Message:</b>\n{message}\n\n"
        f"<i>💡 PRO TIP: Is message ka 'Reply' de kar answer type kar. Tera reply seedha user ko email ho jayega!</i>"
    )

    tg_message_id = None
    
    async with httpx.AsyncClient() as client:
        if screenshot and screenshot.filename:
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            file_bytes = await screenshot.read()
            files = {"photo": (screenshot.filename, file_bytes, screenshot.content_type)}
            data = {"chat_id": admin_id, "caption": msg_text, "parse_mode": "HTML"}
            response = await client.post(url, data=data, files=files)
        else:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            json_payload = {"chat_id": admin_id, "text": msg_text, "parse_mode": "HTML"}
            response = await client.post(url, json=json_payload)
            
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to send ticket to Admin.")
            
        resp_data = response.json()
        tg_message_id = resp_data.get("result", {}).get("message_id")

    ticket_data = {
        "ticket_id": ticket_id,
        "owner": current_user,
        "subject": subject,
        "message": message,
        "has_screenshot": bool(screenshot and screenshot.filename),
        "status": "Open",
        "admin_reply": None,
        "tg_message_id": tg_message_id, 
        "created_at": datetime.utcnow()
    }
    
    await tickets_collection.insert_one(ticket_data)

    return {"status": "success", "message": f"✅ Ticket {ticket_id} created! Admin will reply soon."}

# ==========================================
# 2. GET USER TICKETS (For Frontend Dashboard)
# ==========================================
@router.get("/list")
async def get_my_tickets(current_user: str = Depends(verify_api_key)):
    cursor = tickets_collection.find({"owner": current_user}).sort("created_at", -1)
    tickets = await cursor.to_list(length=50)
    
    for tkt in tickets:
        tkt["_id"] = str(tkt["_id"])
        
    return {"status": "success", "tickets": tickets}
    
