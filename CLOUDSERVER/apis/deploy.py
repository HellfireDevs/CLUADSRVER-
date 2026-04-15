from fastapi import APIRouter, BackgroundTasks, Header, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Server Level Tools
from CLOUDSERVER.core_utils.server_ops import pull_latest_code, restart_pm2, check_pm2_exists, stop_pm2, install_requirements

# 🚀 MongoDB Database Imports
from CLOUDSERVER.database.deploys import register_new_bot, get_bot_by_repo, check_pm2_name_in_db, get_bot_by_name
from CLOUDSERVER.database.user import get_user_by_username # 📧 User email aur GitHub Token nikalne ke liye

# 🛡️ Security Import
from CLOUDSERVER.auth.verify import verify_api_key

router = APIRouter()

# ==========================================
# 📧 EMAIL NOTIFICATION ENGINE
# ==========================================
def send_deployment_email(receiver_email: str, app_name: str, status: str, error_msg: str = ""):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    if not sender_email or not sender_password:
        print("🚨 Email credentials missing in .env")
        return

    msg = MIMEMultipart("alternative")
    
    if status == "success":
        msg["Subject"] = f"✅ Deployment Success: {app_name}"
        html_content = f"""
        <div style="font-family: Arial; padding: 20px; background: #f4f4f9;">
            <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px; border-top: 5px solid #4CAF50;">
                <h2 style="color: #4CAF50;">System Online! 🚀</h2>
                <p>Your application <b>{app_name}</b> has been successfully deployed and is now running on NEX CLOUD.</p>
                <a href="https://cluadwebsite.vercel.app/dashboard" style="display: inline-block; padding: 10px 20px; background: #8a2be2; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px;">Go to Dashboard</a>
            </div>
        </div>
        """
    else:
        msg["Subject"] = f"❌ Deployment Failed: {app_name}"
        html_content = f"""
        <div style="font-family: Arial; padding: 20px; background: #f4f4f9;">
            <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px; border-top: 5px solid #f44336;">
                <h2 style="color: #f44336;">Deployment Crashed 🚨</h2>
                <p>Your application <b>{app_name}</b> failed to start or crashed during deployment.</p>
                <p style="background: #eee; padding: 10px; font-family: monospace; color: #d32f2f;">Error: {error_msg}</p>
                <a href="https://cluadwebsite.vercel.app" style="display: inline-block; padding: 10px 20px; background: #f44336; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px;">View Live Error Logs</a>
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
# 📥 PAYLOAD MODELS
# ==========================================
class NewDeployPayload(BaseModel):
    repo_url: str       
    repo_name: str      
    app_name: str       
    folder_path: str = ""  
    use_docker: bool = False      
    start_cmd: Optional[str] = None 

class ActionPayload(BaseModel):
    app_name: str
    action: str # "stop", "restart", "reset"

# ==========================================
# ⚙️ BACKGROUND DEPLOYMENT ENGINE (With Private Repo Magic)
# ==========================================
async def run_background_update(repo_path: str, pm2_name: str, repo_url: str, use_docker: bool, start_cmd: str, owner: str, is_reset: bool = False):
    """Background engine jo Code Pull karega, Requirements install karega, aur Deploy marega"""
    print(f"🚀 [DEPLOY ENGINE] Initializing for {pm2_name}...")
    
    # 1. User ka data nikalo (Email bhejne ke liye aur GitHub Token ke liye)
    user_info = await get_user_by_username(owner)
    user_email = user_info.get("email") if user_info else None
    github_token = user_info.get("github_token") if user_info else None

    # 🐙 SMART PRIVATE REPO TOKEN INJECTOR
    secure_repo_url = repo_url
    if github_token and repo_url and "github.com" in repo_url and "@github.com" not in repo_url:
        print("🔐 [GITHUB] Private Repo detected. Injecting secure Access Token...")
        secure_repo_url = repo_url.replace("https://github.com/", f"https://{github_token}@github.com/")

    try:
        # Step 1: Smart pull code from GitHub (Token wale URL ke sath)
        pull_latest_code(repo_path, secure_repo_url)
        
        # Step 2: Agar Reset/Redeploy hai, ya naya bot hai, toh requirements download karo
        if not use_docker and is_reset:
            print(f"📦 [DEPLOY ENGINE] Installing dependencies for {pm2_name}...")
            install_requirements(repo_path) 

        # Step 3: PM2 ya Docker Start
        restart_pm2(pm2_name, repo_path, use_docker, start_cmd)
        
        print(f"🔥 [DEPLOY ENGINE] 100% DONE! {pm2_name} is LIVE.")
        
        if user_email:
            send_deployment_email(user_email, pm2_name, "success")
            
    except Exception as e:
        error_msg = str(e)
        print(f"🚨 [DEPLOY CRASH] {error_msg}")
        if user_email:
            send_deployment_email(user_email, pm2_name, "failed", error_msg)

# ==========================================
# 1. NEW DEPLOYMENT API (Auto Folder Path) - 🔥 PREMIUM LOCKED
# ==========================================
@router.post("/deploy-new")
async def create_new_deployment(
    payload: NewDeployPayload,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(verify_api_key) 
):
    # 🛑 THE UNBREAKABLE PREMIUM LOCK
    user_info = await get_user_by_username(current_user)
    if not user_info or not user_info.get("is_premium"):
        raise HTTPException(
            status_code=403, 
            detail="🔒 Premium Plan Required! Upgrade to deploy new applications on NEX CLOUD."
        )

    # Baki saari purani checks
    if not payload.use_docker and not payload.start_cmd:
        raise HTTPException(status_code=400, detail="❌ Bhai, PM2 ke liye start_cmd toh bhej!")

    if not payload.use_docker and check_pm2_exists(payload.app_name):
        raise HTTPException(status_code=400, detail=f"❌ App Name '{payload.app_name}' server pe pehle se taken hai!")
        
    if await check_pm2_name_in_db(payload.app_name):
        raise HTTPException(status_code=400, detail=f"❌ App Name '{payload.app_name}' database mein pehle se taken hai!")

    # 🧠 SMART PATH GENERATOR (Frontend ka kachra path ignore!)
    auto_folder_path = f"/home/ubuntu/nex_cloud_apps/{current_user}/{payload.app_name}"

    # Save to Database
    bot_data = {
        "repo_url": payload.repo_url,    
        "repo_name": payload.repo_name,  
        "pm2_name": payload.app_name,
        "folder_path": auto_folder_path, 
        "use_docker": payload.use_docker,
        "start_cmd": payload.start_cmd,
        "owner": current_user  
    }
    await register_new_bot(bot_data)

    # Naya bot direct deploy pe laga do
    background_tasks.add_task(
        run_background_update, 
        auto_folder_path, payload.app_name, payload.repo_url, 
        payload.use_docker, payload.start_cmd, current_user, True
    )

    return {"status": "success", "message": f"✅ Bot '{payload.app_name}' registered! Deployment started in background."}

# ==========================================
# 2. GITHUB WEBHOOK API
# ==========================================
@router.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks, x_github_event: str = Header(None)):
    if x_github_event == "ping": return {"status": "success", "message": "Webhook Connected!"}
    if x_github_event != "push": return {"status": "ignored"}

    try:
        payload = await request.json()
        incoming_repo_name = payload.get("repository", {}).get("name")
        if not incoming_repo_name: return {"status": "ignored"}

        bot_info = await get_bot_by_repo(incoming_repo_name)
        if not bot_info: return {"status": "ignored"}
            
        background_tasks.add_task(
            run_background_update, 
            bot_info["folder_path"], bot_info["pm2_name"], bot_info.get("repo_url"),
            bot_info.get("use_docker", False), bot_info.get("start_cmd"), bot_info["owner"], False
        )
        return {"status": "success", "message": f"Auto-Update triggered for {bot_info['pm2_name']}!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 3. DASHBOARD CONTROLS (Stop, Restart, Reset)
# ==========================================
@router.post("/action")
async def bot_actions(payload: ActionPayload, background_tasks: BackgroundTasks, current_user: str = Depends(verify_api_key)):
    bot_info = await get_bot_by_name(payload.app_name)
    
    if not bot_info or bot_info["owner"] != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized or Bot not found!")

    try:
        if payload.action == "stop":
            stop_pm2(payload.app_name)
            return {"status": "success", "message": "Bot Stopped!"}
            
        elif payload.action == "restart":
            restart_pm2(payload.app_name, bot_info["folder_path"], bot_info.get("use_docker"), bot_info.get("start_cmd"))
            return {"status": "success", "message": "Bot Restarted!"}
            
        elif payload.action == "reset":
            # Pura code dubara pull karega aur requirements wapas install karega
            background_tasks.add_task(
                run_background_update, 
                bot_info["folder_path"], bot_info["pm2_name"], bot_info.get("repo_url"),
                bot_info.get("use_docker"), bot_info.get("start_cmd"), current_user, True
            )
            return {"status": "success", "message": "Reset & Redeploy initiated!"}
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
