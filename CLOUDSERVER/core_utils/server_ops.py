import subprocess
import os
import json

# ==========================================
# 1. PM2 DUPLICATE CHECKER
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
# 2. SMART GIT ENGINE (Init + Fetch + Reset)
# ==========================================
def pull_latest_code(repo_path: str, repo_url: str = None):
    """
    Smart Clone/Pull: 
    - Agar .git nahi hai -> Init karega, Remote add karega, aur force pull karega (Isse .env delete nahi hogi).
    - Agar hai -> Hard Reset + Pull karega.
    """
    if not os.path.exists(repo_path):
        os.makedirs(repo_path, exist_ok=True)

    # Check agar .git folder exist karta hai
    git_dir = os.path.join(repo_path, ".git")
    
    try:
        if not os.path.exists(git_dir):
            if not repo_url:
                raise Exception("Repo URL missing for first-time setup!")
            
            print(f"🚀 [GIT] First time setup in non-empty folder. Initializing repo...")
            # Git Clone ki jagah Smart Init (Bypasses "Directory not empty" error)
            subprocess.run(["git", "init"], cwd=repo_path, check=True)
            subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=repo_path, check=True)
            subprocess.run(["git", "fetch", "--all"], cwd=repo_path, check=True)
            subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, check=True)
            
            print("✅ [GIT] Successfully pulled code into the folder!")
        else:
            print(f"📥 [GIT] Updating existing code in {repo_path}...")
            subprocess.run(["git", "fetch", "--all"], cwd=repo_path, check=True)
            subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, check=True)
        
        # Dependency update (Requirements install)
        # Check if requirements.txt exists before running pip
        if os.path.exists(os.path.join(repo_path, "requirements.txt")):
            print("📦 [PIP] Installing/Updating requirements...")
            subprocess.run(["pip", "install", "-r", "requirements.txt"], cwd=repo_path, check=True)
        else:
            print("⚠️ [PIP] No requirements.txt found. Skipping pip install.")
            
        return True
    except subprocess.CalledProcessError as e:
        # Pura error terminal se nikal kar print karega
        error_msg = e.stderr.decode() if getattr(e, 'stderr', None) else str(e)
        print(f"❌ [GIT/PIP ERROR]: {error_msg}")
        raise Exception(f"Code setup failed: {error_msg}")
    except Exception as e:
        print(f"❌ [SYSTEM ERROR]: {str(e)}")
        raise Exception(f"Code setup failed: {str(e)}")

# ==========================================
# 3. MASTER DEPLOY ENGINE (Docker + PM2)
# ==========================================
def restart_pm2(app_name: str, folder_path: str, use_docker: bool = False, start_cmd: str = None):
    """Asli Docker build/run ya PM2 start/restart command fire karega"""
    print(f"🔄 [DEPLOY ENGINE] Processing bot: {app_name} (Docker Mode: {use_docker})...")
    
    try:
        if use_docker:
            print(f"🐳 [DOCKER] Building image for {app_name}...")
            # Docker Image Build
            subprocess.run(["docker", "build", "-t", app_name, "."], cwd=folder_path, check=True)
            
            print(f"🧹 [DOCKER] Cleaning up old container (if exists)...")
            # Purane container ko hatana taaki naya naam use kar sakein
            subprocess.run(["docker", "stop", app_name], stderr=subprocess.DEVNULL)
            subprocess.run(["docker", "rm", app_name], stderr=subprocess.DEVNULL)
            
            print(f"🚀 [DOCKER] Running new container for {app_name}...")
            subprocess.run(["docker", "run", "-d", "--name", app_name, app_name], check=True)
            print(f"✅ [DOCKER] {app_name} successfully deployed and running!")
            
        else:
            is_running = check_pm2_exists(app_name)
            
            if not is_running:
                # PM2 mein naya start
                if not start_cmd:
                    raise Exception("❌ PM2 ke liye start_cmd zaroori hai (e.g., 'python3 main.py')")
                
                print(f"🔥 [PM2] Starting newly with CMD: {start_cmd}")
                cmd = ["pm2", "start"] + start_cmd.split() + ["--name", app_name]
                subprocess.run(cmd, cwd=folder_path, check=True)
                print(f"✅ [PM2] {app_name} successfully started!")
                
            else:
                # PM2 mein restart
                print(f"🔄 [PM2] Restarting existing bot: {app_name}...")
                subprocess.run(["pm2", "restart", app_name], check=True, capture_output=True)
                print(f"✅ [PM2] {app_name} successfully restarted!")
                
        return True
        
    except subprocess.CalledProcessError as e:
        # Subprocess ke terminal errors ko capture karna
        error_msg = e.stderr.decode() if getattr(e, 'stderr', None) else str(e)
        print(f"❌ [DEPLOY ERROR]: {error_msg}")
        raise Exception(f"Deployment Failed: {error_msg}")
    except Exception as e:
        print(f"❌ [SYSTEM ERROR]: {str(e)}")
        raise Exception(f"Deployment System Error: {str(e)}")
        
