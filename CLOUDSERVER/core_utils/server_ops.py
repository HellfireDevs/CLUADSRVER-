import subprocess
import os

def pull_latest_code(repo_path: str):
    """Asli Git Pull command fire karega us folder mein"""
    print(f"📥 [GIT] Pulling latest code in {repo_path}...")
    
    if not os.path.exists(repo_path):
        raise Exception(f"❌ Folder nahi mila: {repo_path}")

    try:
        # Puraani changes ko discard karke force pull (taaki conflict na aaye)
        subprocess.run(["git", "fetch", "--all"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, check=True, capture_output=True)
        
        print("✅ [GIT] Successfully pulled latest code!")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"❌ [GIT ERROR]: {error_msg}")
        raise Exception(f"Git Pull Failed: {error_msg}")

def restart_pm2(app_name: str):
    """Asli PM2 restart command fire karega"""
    print(f"🔄 [PM2] Restarting bot: {app_name}...")
    try:
        subprocess.run(["pm2", "restart", app_name], check=True, capture_output=True)
        print(f"✅ [PM2] {app_name} successfully restarted!")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"❌ [PM2 ERROR]: {error_msg}")
        raise Exception(f"PM2 Restart Failed: {error_msg}")
      
