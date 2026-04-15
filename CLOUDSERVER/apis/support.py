import os
import random
import string
from datetime import datetime
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from CLOUDSERVER.database.database import tickets_collection
from CLOUDSERVER.auth.verify import verify_api_key

router = APIRouter()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")

class TicketPayload(BaseModel):
    subject: str
    message: str

def generate_ticket_id():
    return "TKT-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ==========================================
# 1. CREATE SUPPORT TICKET
# ==========================================
@router.post("/create")
async def create_ticket(payload: TicketPayload, current_user: str = Depends(verify_api_key)):
    ticket_id = generate_ticket_id()
    
    # 1. Message for Admin (Telegram)
    msg_text = (
        f"🎫 <b>NEW SUPPORT TICKET</b> 🎫\n\n"
        f"👤 <b>User:</b> <code>{current_user}</code>\n"
        f"🔖 <b>Ticket ID:</b> <code>{ticket_id}</code>\n"
        f"📌 <b>Subject:</b> {payload.subject}\n\n"
        f"📝 <b>Message:</b>\n{payload.message}\n\n"
        f"<i>💡 PRO TIP: Is message ka 'Reply' de kar answer type kar. Tera reply seedha user ko email ho jayega!</i>"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # 2. Telegram pe bhej aur message_id save kar
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "chat_id": TELEGRAM_ADMIN_ID,
            "text": msg_text,
            "parse_mode": "HTML"
        })
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to send ticket to Admin.")
            
        resp_data = response.json()
        tg_message_id = resp_data["result"]["message_id"] # Ye ID track karegi tera reply

    # 3. Database mein save karo
    ticket_data = {
        "ticket_id": ticket_id,
        "owner": current_user,
        "subject": payload.subject,
        "message": payload.message,
        "status": "Open",
        "admin_reply": None,
        "tg_message_id": tg_message_id, # Is ID se pata chalega tu kis ticket pe reply kar raha hai
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
  
