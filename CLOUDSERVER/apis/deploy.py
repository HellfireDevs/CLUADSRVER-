from fastapi import APIRouter, BackgroundTasks, Header, Request, HTTPException
from CLOUDSERVER.core_utils.server_ops import pull_latest_code, restart_pm2

router = APIRouter()

# ==========================================
# THE REAL DEPLOYMENT ENGINE 
# ==========================================
def run_real_deployment(repo_path: str, pm2_name: str):
    print("🚀 [DEPLOY] Real deployment sequence initiated...")
    try:
        # STEP 1: Asli Git Pull
        pull_latest_code(repo_path)
        
        # STEP 2: Asli Server Restart
        restart_pm2(pm2_name)
        
        print("🔥 [DEPLOY] 100% DONE! Bot is now running on latest code.")
    except Exception as e:
        print(f"🚨 [DEPLOY CRASH] Deployment failed midway: {str(e)}")


# ==========================================
# THE WEBHOOK ENDPOINT
# ==========================================
@router.post("/deploy")
async def auto_deploy(
    request: Request, 
    background_tasks: BackgroundTasks, 
    x_github_event: str = Header(None)
):
    if x_github_event == "ping":
        return {"status": "success", "message": "GitHub connected!"}
        
    if x_github_event != "push":
        return {"status": "ignored"}

    # Tera bot ka path aur PM2 name (Isko tu baad mein dynamic bhi kar sakta hai)
    BOT_FOLDER_PATH = "/home/ubuntu/MYRDLMUSIC"  # <--- Apna path check kar lena
    PM2_APP_NAME = "MyRdlBot"                    # <--- PM2 mein jo naam hai
    
    # Real background task start kar diya
    background_tasks.add_task(run_real_deployment, BOT_FOLDER_PATH, PM2_APP_NAME)
    
    return {
        "status": "success",
        "message": "🔥 Real deployment triggered! GitHub code is being pulled and PM2 is restarting."
    }
  
