import subprocess
import os
import json

# ==========================================
# 1. PM2 DUPLICATE CHECKER (Naya Function)
# ==========================================
def check_pm2_exists(app_name: str) -> bool:
    """Check karega ki PM2 mein ye naam pehle se toh nahi chal raha"""
    print(f"🔍 [PM2] Checking if '{app_name}' already exists...")
    try:
        # PM2 ki list JSON format mein nikalna
        result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True)
        apps = json.loads(result.stdout)
        
        # Check karna ki naam list mein hai ya nahi
        for app in apps:
            if app.get("name") == app_name:
                print(f"⚠️ [PM2] App '{app_name}' pehle se exist karta hai!")
                return True
                
        print(f"✅ [PM2] App '{app_name}' available hai.")
        return False
    except Exception as e:
        print(f"❌ [PM2 CHECK ERROR]: {str(e)}")
        # Agar error aaye toh safe side False return karo taaki crash na ho
        return False

# ==========================================
# 2. GIT PULL ENGINE
# ==========================================
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

# ==========================================
# 3. PM2 RESTART ENGINE
# ==========================================
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
        
