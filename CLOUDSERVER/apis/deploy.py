from fastapi import APIRouter, BackgroundTasks, Header, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os
import smtplib
import asyncio 
import re 
import hmac       
import hashlib    
import time       
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Server Level Tools
from CLOUDSERVER.core_utils.server_ops import pull_latest_code, restart_pm2, check_pm2_exists, stop_pm2, install_requirements, clear_pm2_logs

# 🚀 MongoDB Database Imports
from CLOUDSERVER.database.deploys import register_new_bot, get_bot_by_repo, check_pm2_name_in_db, get_bot_by_name, toggle_auto_deploy, set_update_pending
from CLOUDSERVER.database.user import get_user_by_username 

# 🛡️ Security Import
from CLOUDSERVER.auth.verify import verify_api_key

router = APIRouter()

# ==========================================
# 🛑 IN-BUILT RATE LIMITER (Spam Blocker)
# ==========================================
DEPLOY_LIMITS = {}
async def deploy_rate_limit(request: Request):
    """Ek IP se 1 minute mein max 5 requests allowed hain"""
    client_ip = request.headers.get("x-forwarded-for", request.client.host)
    current_time = time.time()
    
    if client_ip not in DEPLOY_LIMITS:
        DEPLOY_LIMITS[client_ip] = []
        
    DEPLOY_LIMITS[client_ip] = [t for t in DEPLOY_LIMITS[client_ip] if current_time - t < 60]
    
    if len(DEPLOY_LIMITS[client_ip]) >= 5:
        print(f"🚨 [RATE LIMIT] Spam blocked from IP: {client_ip}")
        raise HTTPException(status_code=429, detail="⚠️ Too Many Requests! Spamming is not allowed. Try again in a minute.")
        
    DEPLOY_LIMITS[client_ip].append(current_time)

# ==========================================
# 📧 EMAIL NOTIFICATION ENGINE
# ==========================================
def send_deployment_email(receiver_email: str, app_name: str, status: str, error_msg: str = ""):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    if not sender_email or not sender_password:
        return

    msg = MIMEMultipart("alternative")
    if status == "success":
        msg["Subject"] = f"✅ Deployment Success: {app_name}"
        html_content = f"""
        <div style="font-family: Arial; padding: 20px; background: #f4f4f9;">
            <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px; border-top: 5px solid #4CAF50;">
                <h2 style="color: #4CAF50;">System Online! 🚀</h2>
                <p>Your application <b>{app_name}</b> has been successfully deployed and is now running on NEX CLOUD.</p>
            </div>
        </div>
        """
    else:
        msg["Subject"] = f"❌ Deployment Failed: {app_name}"
        html_content = f"""
        <div style="font-family: Arial; padding: 20px; background: #f4f4f9;">
            <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px; border-top: 5px solid #f44336;">
                <h2 style="color: #f44336;">Deployment Crashed 🚨</h2>
                <p>Error details: {error_msg}</p>
            </div>
        </div>
        """

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


# ==========================================
# 📥 PAYLOAD MODELS (MODULAR)
# ==========================================
class PPAM2DeployPayload(BaseModel):
    repo_url: str       
    repo_name: str      
    app_name: str       
    start_cmd: str      

class VIPPM2DeployPayload(BaseModel):
    repo_url: str       
    repo_name: str      
    app_name: str       
    start_cmd: str      

class DockerDeployPayload(BaseModel):
    repo_url: str       
    repo_name: str      
    app_name: str       
    # Docker mode mein backend auto-detect karega

class ActionPayload(BaseModel):
    app_name: str
    action: str 

class AutoDeployTogglePayload(BaseModel): 
    app_name: str
    status: bool

# ==========================================
# ⚙️ BACKGROUND DEPLOYMENT ENGINE
# ==========================================
async def run_background_update(repo_path: str, pm2_name: str, repo_url: str, use_docker: bool, start_cmd: str, owner: str, is_reset: bool = False):
    print(f"🚀 [DEPLOY ENGINE] Initializing for {pm2_name}...")
    
    user_info = await get_user_by_username(owner)
    user_email = user_info.get("email") if user_info else None
    github_token = user_info.get("github_token") if user_info else None

    secure_repo_url = repo_url
    if github_token and repo_url and "github.com" in repo_url and "@github.com" not in repo_url:
        print("🔐 [GITHUB] Secure Access Token Injected")
        secure_repo_url = repo_url.replace("https://github.com/", f"https://{github_token}@github.com/")

    try:
        await asyncio.to_thread(pull_latest_code, repo_path, secure_repo_url)
        
        if not use_docker and is_reset:
            await asyncio.to_thread(install_requirements, repo_path) 

        await asyncio.to_thread(restart_pm2, pm2_name, repo_path, use_docker, start_cmd)
        
        print(f"🔥 [DEPLOY ENGINE] 100% DONE! {pm2_name} is LIVE.")
        if user_email:
            send_deployment_email(user_email, pm2_name, "success")
            
    except Exception as e:
        error_msg = str(e).replace(github_token, "***HIDDEN_TOKEN***") if github_token else str(e)
        print(f"🚨 [DEPLOY CRASH] {error_msg}")
        if user_email:
            send_deployment_email(user_email, pm2_name, "failed", error_msg)


# ==========================================
# 🚀 1. PPAM2 ENDPOINT (PUBLIC DOCKERIZED PM2)
# ==========================================
@router.post("/deploy-ppam2", dependencies=[Depends(deploy_rate_limit)])
async def deploy_ppam2(payload: PPAM2DeployPayload, background_tasks: BackgroundTasks, current_user: str = Depends(verify_api_key)):
    if not re.match(r'^[a-zA-Z0-9_-]+$', payload.app_name):
        raise HTTPException(status_code=400, detail="❌ Invalid App Name! Only letters, numbers, hyphens, and underscores allowed.")
        
    cmd_parts = payload.start_cmd.strip().split()
    if not cmd_parts or cmd_parts[0] not in {"python", "python3", "node", "npm", "yarn", "bash", "sh"}:
        raise HTTPException(status_code=400, detail="❌ Blocked! Invalid start command.")
    if "-c" in cmd_parts or "-e" in cmd_parts or "--eval" in cmd_parts:
        raise HTTPException(status_code=400, detail="❌ Hacker Alert! Inline execution blocked.")

    user_info = await get_user_by_username(current_user)
    if not user_info or not user_info.get("is_premium"):
        raise HTTPException(status_code=403, detail="🔒 Premium Plan Required!")

    if await check_pm2_name_in_db(payload.app_name):
        raise HTTPException(status_code=400, detail="❌ App Name database mein pehle se taken hai!")

    auto_folder_path = f"/home/ubuntu/nex_cloud_apps/{current_user}/{payload.app_name}"

    bot_data = {
        "repo_url": payload.repo_url, "repo_name": payload.repo_name, "pm2_name": payload.app_name,
        "folder_path": auto_folder_path, "use_docker": True, "start_cmd": payload.start_cmd,
        "owner": current_user, "auto_deploy": True, "update_pending": False 
    }
    await register_new_bot(bot_data)

    background_tasks.add_task(run_background_update, auto_folder_path, payload.app_name, payload.repo_url, True, payload.start_cmd, current_user, True)
    return {"status": "success", "message": f"✅ PPAM2 Bot '{payload.app_name}' registered! Building Safe Container..."}

# ==========================================
# 👑 2. VIP PM2 ENDPOINT (TERA ADMIN MODE)
# ==========================================
@router.post("/deploy-vip-pm2", dependencies=[Depends(deploy_rate_limit)])
async def deploy_vip_pm2(payload: VIPPM2DeployPayload, background_tasks: BackgroundTasks, current_user: str = Depends(verify_api_key)):
    if not re.match(r'^[a-zA-Z0-9_-]+$', payload.app_name):
        raise HTTPException(status_code=400, detail="❌ Invalid App Name!")
        
    cmd_parts = payload.start_cmd.strip().split()
    if not cmd_parts or cmd_parts[0] not in {"python", "python3", "node", "npm", "yarn", "bash", "sh", "pm2"}:
        raise HTTPException(status_code=400, detail="❌ Blocked! Invalid start command.")

    user_info = await get_user_by_username(current_user)
    
    if not user_info.get("pm2_access", False):
        raise HTTPException(status_code=403, detail="🔒 VIP PM2 Access Restricted! You need Admin approval.")

    if check_pm2_exists(payload.app_name) or await check_pm2_name_in_db(payload.app_name):
        raise HTTPException(status_code=400, detail="❌ App Name server pe pehle se taken hai!")

    auto_folder_path = f"/home/ubuntu/nex_cloud_apps/{current_user}/{payload.app_name}"

    bot_data = {
        "repo_url": payload.repo_url, "repo_name": payload.repo_name, "pm2_name": payload.app_name,
        "folder_path": auto_folder_path, "use_docker": False, "start_cmd": payload.start_cmd, 
        "owner": current_user, "auto_deploy": True, "update_pending": False 
    }
    await register_new_bot(bot_data)

    background_tasks.add_task(run_background_update, auto_folder_path, payload.app_name, payload.repo_url, False, payload.start_cmd, current_user, True)
    return {"status": "success", "message": f"✅ VIP Bot '{payload.app_name}' started directly on Server!"}

# ==========================================
# 🐳 3. PURE DOCKER ENDPOINT
# ==========================================
@router.post("/deploy-docker", dependencies=[Depends(deploy_rate_limit)])
async def deploy_pure_docker(payload: DockerDeployPayload, background_tasks: BackgroundTasks, current_user: str = Depends(verify_api_key)):
    if not re.match(r'^[a-zA-Z0-9_-]+$', payload.app_name):
        raise HTTPException(status_code=400, detail="❌ Invalid App Name!")

    user_info = await get_user_by_username(current_user)
    if not user_info or not user_info.get("is_premium"):
        raise HTTPException(status_code=403, detail="🔒 Premium Plan Required!")

    if await check_pm2_name_in_db(payload.app_name):
        raise HTTPException(status_code=400, detail="❌ App Name taken!")

    auto_folder_path = f"/home/ubuntu/nex_cloud_apps/{current_user}/{payload.app_name}"

    bot_data = {
        "repo_url": payload.repo_url, "repo_name": payload.repo_name, "pm2_name": payload.app_name,
        "folder_path": auto_folder_path, "use_docker": True, "start_cmd": None, 
        "owner": current_user, "auto_deploy": True, "update_pending": False 
    }
    await register_new_bot(bot_data)

    background_tasks.add_task(run_background_update, auto_folder_path, payload.app_name, payload.repo_url, True, None, current_user, True)
    return {"status": "success", "message": f"✅ Docker Bot '{payload.app_name}' building from repository!"}

# ==========================================
# 2. GITHUB WEBHOOK API (🔒 SECURED WITH HMAC)
# ==========================================
@router.post("/webhook")
async def github_webhook(
    request: Request, 
    background_tasks: BackgroundTasks, 
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None) 
):
    if x_github_event == "ping": return {"status": "success", "message": "Webhook Connected!"}
    if x_github_event != "push": return {"status": "ignored"}

    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="🚨 Server Misconfiguration: GITHUB_WEBHOOK_SECRET is not set!")
        
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Missing GitHub Signature!")
        
    body = await request.body()
    mac = hmac.new(webhook_secret.encode(), msg=body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + mac.hexdigest()
    
    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        print("🚨 [WEBHOOK] HACK ATTEMPT: Invalid Signature!")
        raise HTTPException(status_code=403, detail="Invalid Signature! Nice try Hacker.")

    try:
        payload = await request.json()
        incoming_repo_name = payload.get("repository", {}).get("name")
        if not incoming_repo_name: return {"status": "ignored"}

        bot_info = await get_bot_by_repo(incoming_repo_name)
        if not bot_info: return {"status": "ignored"}
            
        if bot_info.get("auto_deploy") is False:
            await set_update_pending(bot_info['pm2_name'], True) 
            return {"status": "success", "message": "Update detected, waiting for manual approval."}

        background_tasks.add_task(
            run_background_update, 
            bot_info["folder_path"], bot_info["pm2_name"], bot_info.get("repo_url"),
            bot_info.get("use_docker", False), bot_info.get("start_cmd"), bot_info["owner"], False
        )
        return {"status": "success", "message": f"Auto-Update triggered for {bot_info['pm2_name']}!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 3. DASHBOARD CONTROLS (WITH RATE LIMIT)
# ==========================================
@router.post("/action", dependencies=[Depends(deploy_rate_limit)])
async def bot_actions(payload: ActionPayload, background_tasks: BackgroundTasks, current_user: str = Depends(verify_api_key)):
    bot_info = await get_bot_by_name(payload.app_name)
    
    if not bot_info or bot_info["owner"] != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized or Bot not found!")

    try:
        if payload.action == "stop":
            await asyncio.to_thread(stop_pm2, payload.app_name)
            return {"status": "success", "message": "Bot Stopped!"}
            
        elif payload.action == "restart":
            await asyncio.to_thread(restart_pm2, payload.app_name, bot_info["folder_path"], bot_info.get("use_docker"), bot_info.get("start_cmd"))
            return {"status": "success", "message": "Bot Restarted!"}
            
        elif payload.action == "reset":
            await set_update_pending(payload.app_name, False)
            background_tasks.add_task(
                run_background_update, 
                bot_info["folder_path"], bot_info["pm2_name"], bot_info.get("repo_url"),
                bot_info.get("use_docker"), bot_info.get("start_cmd"), current_user, True
            )
            return {"status": "success", "message": "Reset & Redeploy initiated!"}
            
        elif payload.action == "clear_logs":
            success = await asyncio.to_thread(clear_pm2_logs, payload.app_name)
            if success:
                return {"status": "success", "message": f"Logs for {payload.app_name} cleared successfully!"}
            else:
                raise HTTPException(status_code=500, detail="Failed to clear logs.")
                
        elif payload.action == "git_pull":
            await set_update_pending(payload.app_name, False)
            background_tasks.add_task(
                run_background_update, 
                bot_info["folder_path"], bot_info["pm2_name"], bot_info.get("repo_url"),
                bot_info.get("use_docker"), bot_info.get("start_cmd"), current_user, False 
            )
            return {"status": "success", "message": "Pulling latest code & Restarting..."}

        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 4. TOGGLE AUTO-DEPLOY 
# ==========================================
@router.post("/toggle-autodeploy")
async def toggle_webhook_status(payload: AutoDeployTogglePayload, current_user: str = Depends(verify_api_key)):
    bot_info = await get_bot_by_name(payload.app_name)
    if not bot_info or bot_info.get("owner") != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized!")
    await toggle_auto_deploy(payload.app_name, payload.status)
    return {"status": "success", "message": f"✅ Auto-Deploy turned {'ON' if payload.status else 'OFF'}!"}

# ==========================================
# 🛠️ EDIT POINTS (DB Update Functions)
# ==========================================
async def update_bot_repo_details(app_name: str, new_repo_url: str, new_start_cmd: str, new_repo_name: str):
    from CLOUDSERVER.database.database import deploys_collection
    result = await deploys_collection.update_one(
        {"pm2_name": app_name},
        {"$set": {"repo_url": new_repo_url, "repo_name": new_repo_name, "start_cmd": new_start_cmd}}
    )
    return result.modified_count > 0

async def update_bot_env_vars(app_name: str, env_data: dict):
    from CLOUDSERVER.database.database import deploys_collection
    result = await deploys_collection.update_one(
        {"pm2_name": app_name},
        {"$set": {"env_vars": env_data}}
    )
    return result.modified_count > 0
    
async def delete_bot_from_db(app_name: str):
    from CLOUDSERVER.database.database import deploys_collection
    result = await deploys_collection.delete_one({"pm2_name": app_name})
    return result.deleted_count > 0
    
