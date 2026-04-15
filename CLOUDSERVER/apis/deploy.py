from fastapi import APIRouter, BackgroundTasks, Header, Request, HTTPException
from pydantic import BaseModel
import json
import os
from CLOUDSERVER.core_utils.server_ops import pull_latest_code, restart_pm2, check_pm2_exists

router = APIRouter()

# ==========================================
# 🧠 MINI DATABASE (Dynamic Storage)
# ==========================================
DB_FILE = "bots_db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==========================================
# 📥 USER INPUT PAYLOAD FORMAT
# ==========================================
class NewDeployPayload(BaseModel):
    repo_name: str      # GitHub pe repo ka naam (e.g., "MYRDLMUSIC")
    app_name: str       # PM2 ka unique naam (e.g., "user1_bot")
    folder_path: str    # VPS mein kahan code rakha hai

# ==========================================
# 1. NEW DEPLOYMENT API (For Users/Frontend)
# ==========================================
@router.post("/deploy-new")
async def create_new_deployment(payload: NewDeployPayload):
    """
    Jab user apni website se naya bot setup karega toh ye API hit hogi.
    """
    # 🚨 CHECK 1: PM2 Duplicate Name Checker
    if check_pm2_exists(payload.app_name):
        raise HTTPException(
            status_code=400, 
            detail=f"❌ App Name '{payload.app_name}' pehle se taken hai. Koi aur naam choose kar!"
        )

    # 💾 CHECK 2: Database mein save karna
    db = load_db()
    db[payload.repo_name] = {
        "folder_path": payload.folder_path,
        "pm2_name": payload.app_name
    }
    save_db(db)

    return {
        "status": "success",
        "message": f"✅ Bot '{payload.app_name}' successfully registered! Ab tum webhook ya restart API use kar sakte ho."
    }

# ==========================================
# 2. GITHUB WEBHOOK API (For Auto-Updates)
# ==========================================
def run_background_update(repo_path: str, pm2_name: str):
    print(f"🚀 [UPDATE] Updating code for {pm2_name}...")
    try:
        pull_latest_code(repo_path)
        restart_pm2(pm2_name)
        print(f"🔥 [UPDATE] 100% DONE! {pm2_name} is updated.")
    except Exception as e:
        print(f"🚨 [UPDATE CRASH] {str(e)}")

@router.post("/webhook")
async def github_webhook(
    request: Request, 
    background_tasks: BackgroundTasks, 
    x_github_event: str = Header(None)
):
    """
    GitHub ispe hit karega code push hone ke baad.
    """
    if x_github_event == "ping":
        return {"status": "success", "message": "GitHub Webhook Connected!"}
    
    if x_github_event != "push":
        return {"status": "ignored"}

    try:
        payload = await request.json()
        repo_name = payload.get("repository", {}).get("name")
        
        # Database mein check karo
        db = load_db()
        if not repo_name or repo_name not in db:
            return {"status": "ignored", "message": "Ye repo server pe registered nahi hai."}
            
        bot_info = db[repo_name]
        
        # Background task
        background_tasks.add_task(run_background_update, bot_info["folder_path"], bot_info["pm2_name"])
        
        return {"status": "success", "message": f"Update triggered for {bot_info['pm2_name']}!"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
