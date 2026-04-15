from fastapi import APIRouter, BackgroundTasks, Header, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os

# Server Level Tools
from CLOUDSERVER.core_utils.server_ops import pull_latest_code, restart_pm2, check_pm2_exists

# 🚀 Naya MongoDB Database Imports
from CLOUDSERVER.database.deploys import register_new_bot, get_bot_by_repo, check_pm2_name_in_db

# 🛡️ Security Import (Owner pehchanne ke liye)
from CLOUDSERVER.auth.verify import verify_api_key

router = APIRouter()

# ==========================================
# 📥 USER INPUT PAYLOAD FORMAT (UPDATED)
# ==========================================
class NewDeployPayload(BaseModel):
    repo_url: str       # GitHub ka poora link (e.g., "https://github.com/HellfireDevs/YUKIMUSICS.git")
    repo_name: str      # Sirf repo ka naam webhook ke liye (e.g., "YUKIMUSICS")
    app_name: str       # PM2/Docker ka unique naam (e.g., "user1_bot")
    folder_path: str    # VPS mein kahan code rakha hai
    use_docker: bool = False      # Default: PM2 use karega
    start_cmd: Optional[str] = None # Docker ke liye Optional, PM2 ke liye Required

# ==========================================
# 1. NEW DEPLOYMENT API (Secure + MongoDB)
# ==========================================
@router.post("/deploy-new")
async def create_new_deployment(
    payload: NewDeployPayload,
    current_user: str = Depends(verify_api_key) # 🔐 API key check karke Owner ka naam (username) aayega
):
    """
    Jab user apni website se naya bot setup karega toh ye API hit hogi.
    """
    # 🚨 CHECK 0: Agar Docker nahi hai, toh start_cmd zaroori hai
    if not payload.use_docker and not payload.start_cmd:
        raise HTTPException(status_code=400, detail="❌ Bhai, PM2 ke liye start_cmd toh bhej (e.g., 'python3 main.py')!")

    # 🚨 CHECK 1: PM2 Duplicate Name Checker (Server aur Database dono mein check karega)
    # Docker use kar raha hai toh pm2 list mein check skip kar sakte hain, par DB mein uniqueness zaroori hai
    if not payload.use_docker and check_pm2_exists(payload.app_name):
        raise HTTPException(status_code=400, detail=f"❌ App Name '{payload.app_name}' server pe pehle se taken hai!")
        
    if await check_pm2_name_in_db(payload.app_name):
        raise HTTPException(status_code=400, detail=f"❌ App Name '{payload.app_name}' database mein pehle se taken hai. Koi aur naam choose kar!")

    # 💾 CHECK 2: MongoDB mein User (Owner) ke naam ke sath save karna
    bot_data = {
        "repo_url": payload.repo_url,    
        "repo_name": payload.repo_name,  
        "pm2_name": payload.app_name,
        "folder_path": payload.folder_path,
        "use_docker": payload.use_docker,
        "start_cmd": payload.start_cmd,
        "owner": current_user  
    }
    
    await register_new_bot(bot_data)

    return {
        "status": "success",
        "message": f"✅ Bot '{payload.app_name}' successfully registered for {current_user}! Ab tum webhook ya deploy hit kar sakte ho."
    }

# ==========================================
# 2. GITHUB WEBHOOK API (For Auto-Updates)
# ==========================================
def run_background_update(repo_path: str, pm2_name: str, repo_url: str, use_docker: bool, start_cmd: str):
    """Background engine jo Code Pull karega aur Smart Restart/Deploy marega"""
    print(f"🚀 [UPDATE] Updating code for {pm2_name}...")
    try:
        # Smart pull (init + fetch bypass logic use karega)
        pull_latest_code(repo_path, repo_url)
        # Naya master engine: PM2 vs Docker handle karega
        restart_pm2(pm2_name, repo_path, use_docker, start_cmd)
        print(f"🔥 [UPDATE] 100% DONE! {pm2_name} is successfully updated and running.")
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
        
        # 🚨 Webhook sirf "YUKIMUSICS" jaisa naam bhejta hai
        incoming_repo_name = payload.get("repository", {}).get("name")
        
        if not incoming_repo_name:
            return {"status": "ignored", "message": "Repository name not found in payload."}

        # 🔍 MongoDB mein Repo check karo
        bot_info = await get_bot_by_repo(incoming_repo_name)
        
        if not bot_info:
            return {"status": "ignored", "message": f"Repo '{incoming_repo_name}' server pe registered nahi hai."}
            
        # Background task trigger kar do naye parameters ke sath
        background_tasks.add_task(
            run_background_update, 
            bot_info["folder_path"], 
            bot_info["pm2_name"],
            bot_info.get("repo_url"),
            bot_info.get("use_docker", False),
            bot_info.get("start_cmd")
        )
        
        return {"status": "success", "message": f"Update triggered for {bot_info['pm2_name']}!"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
