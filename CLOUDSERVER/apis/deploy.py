from fastapi import APIRouter, BackgroundTasks, Header, Request, HTTPException
from CLOUDSERVER.core_utils.server_ops import pull_latest_code, restart_pm2

router = APIRouter()

# ==========================================
# 🧠 THE BOT REGISTRY (Smart Mapping)
# ==========================================
# GitHub Repo Name : VPS Folder Path & PM2 Name
BOT_REGISTRY = {
    "MYRDLMUSIC": {  # <--- Tere GitHub Repo ka exact naam
        "folder_path": "/home/ubuntu/MYRDLMUSIC",
        "pm2_name": "MyRdlBot"
    },
    "ClientBot_Repo": {  # <--- Future mein koi dusra bot banayega uske liye
        "folder_path": "/home/ubuntu/ClientBot",
        "pm2_name": "service_1"
    }
}

# ==========================================
# THE REAL DEPLOYMENT ENGINE 
# ==========================================
def run_real_deployment(repo_path: str, pm2_name: str):
    print(f"🚀 [DEPLOY] Real deployment sequence initiated for {pm2_name}...")
    try:
        # STEP 1: Asli Git Pull
        pull_latest_code(repo_path)
        
        # STEP 2: Asli Server Restart
        restart_pm2(pm2_name)
        
        print(f"🔥 [DEPLOY] 100% DONE! {pm2_name} is now running on latest code.")
    except Exception as e:
        print(f"🚨 [DEPLOY CRASH] Deployment failed midway for {pm2_name}: {str(e)}")


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

    try:
        payload = await request.json()
        
        # GitHub se pata karo kis Repo mein change hua hai
        repo_name = payload.get("repository", {}).get("name")
        
        # Check karo VPS pe wo repo registered hai ya nahi
        if not repo_name or repo_name not in BOT_REGISTRY:
            return {"status": "ignored", "message": f"Repo '{repo_name}' not found in server registry."}
            
        bot_info = BOT_REGISTRY[repo_name]
        
        # Real background task us specific bot ke liye start kar diya
        background_tasks.add_task(run_real_deployment, bot_info["folder_path"], bot_info["pm2_name"])
        
        return {
            "status": "success",
            "message": f"🔥 Real deployment triggered for {bot_info['pm2_name']}!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
