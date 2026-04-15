import subprocess
import os
import json

# ==========================================
# 1. PM2 DUPLICATE CHECKER & STOPPER
# ==========================================
def check_pm2_exists(app_name: str) -> bool:
    """Check karega ki PM2 mein ye naam pehle se toh nahi chal raha"""
    print(f"🔍 [PM2] Checking if '{app_name}' already exists...")
    try:
        result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True)
        apps = json.loads(result.stdout)
        
        for app in apps:
            if app.get("name") == app_name:
                print(f"⚠️ [PM2] App '{app_name}' pehle se exist karta hai!")
                return True
                
        print(f"✅ [PM2] App '{app_name}' available hai.")
        return False
    except Exception as e:
        print(f"❌ [PM2 CHECK ERROR]: {str(e)}")
        return False

def stop_pm2(app_name: str):
    """Dashboard se PM2 bot ko stop karne ke liye"""
    print(f"🛑 [PM2] Stopping bot: {app_name}...")
    try:
        subprocess.run(["pm2", "stop", app_name], check=False)
        print(f"✅ [PM2] {app_name} stopped.")
    except Exception as e:
        print(f"❌ [PM2 STOP ERROR]: {str(e)}")


# ==========================================
# 2. SMART GIT ENGINE (Init + Fetch + Reset + Clean + VENV)
# ==========================================
def install_requirements(folder_path: str):
    """VENV ke andar specific requirements install karne ke liye (Reset ke time kaam ayega)"""
    venv_path = os.path.join(folder_path, "venv")
    pip_path = os.path.join(venv_path, "bin", "pip")
    
    if os.path.exists(os.path.join(folder_path, "requirements.txt")):
        print("📦 [PIP] Installing/Updating requirements into isolated VENV...")
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], cwd=folder_path, check=True)
    else:
        print("⚠️ [PIP] No requirements.txt found. Skipping pip install.")


def pull_latest_code(repo_path: str, repo_url: str = None):
    """
    Smart Clone/Pull & Auto-VENV with GUNDA FORCE PULL (Clean + Reset)
    """
    if not os.path.exists(repo_path):
        os.makedirs(repo_path, exist_ok=True)

    git_dir = os.path.join(repo_path, ".git")
    
    try:
        # --- GIT LOGIC ---
        if not os.path.exists(git_dir):
            if not repo_url:
                raise Exception("Repo URL missing for first-time setup!")
            
            print(f"🚀 [GIT] First time setup. Initializing repo...")
            subprocess.run(["git", "init"], cwd=repo_path, check=True)
            subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=repo_path, check=True)
            subprocess.run(["git", "fetch", "--all"], cwd=repo_path, check=True)
            
            # Smart Branch Resolver (main vs master)
            try:
                subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, check=True)
            except:
                subprocess.run(["git", "reset", "--hard", "origin/master"], cwd=repo_path, check=True)
                
            print("✅ [GIT] Successfully pulled code into the folder!")
        else:
            print(f"📥 [GIT] Updating existing code in {repo_path}...")
            subprocess.run(["git", "fetch", "--all"], cwd=repo_path, check=True)
            
            # 💣 GUNDA LOGIC: Force clean untracked garbage before reset!
            print(f"🧹 [GIT] Sweeping local untracked changes...")
            subprocess.run(["git", "clean", "-fd"], cwd=repo_path, check=True) 
            
            try:
                subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, check=True)
            except:
                subprocess.run(["git", "reset", "--hard", "origin/master"], cwd=repo_path, check=True)
        
        # --- VENV LOGIC ---
        venv_path = os.path.join(repo_path, "venv")
        
        if not os.path.exists(venv_path):
            print("🏗️ [VENV] Creating isolated Virtual Environment...")
            subprocess.run(["python3", "-m", "venv", "venv"], cwd=repo_path, check=True)
        
        # Install requirements via VENV
        install_requirements(repo_path)
            
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if getattr(e, 'stderr', None) else str(e)
        print(f"❌ [GIT/VENV ERROR]: {error_msg}")
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
            # 🐳 DOCKER LOWERCASE FIX: Uppercase names se build crash hota tha, ab nahi hoga!
            docker_app_name = app_name.lower()
            print(f"🐳 [DOCKER] Building image for {docker_app_name}...")
            subprocess.run(["docker", "build", "-t", docker_app_name, "."], cwd=folder_path, check=True)
            
            print(f"🧹 [DOCKER] Cleaning up old container (if exists)...")
            subprocess.run(["docker", "stop", docker_app_name], stderr=subprocess.DEVNULL)
            subprocess.run(["docker", "rm", docker_app_name], stderr=subprocess.DEVNULL)
            
            print(f"🚀 [DOCKER] Running new container for {docker_app_name}...")
            subprocess.run(["docker", "run", "-d", "--name", docker_app_name, docker_app_name], check=True)
            print(f"✅ [DOCKER] {docker_app_name} successfully deployed and running!")
            
        else:
            is_running = check_pm2_exists(app_name)
            
            if not is_running:
                if not start_cmd:
                    raise Exception("❌ PM2 ke liye start_cmd zaroori hai (e.g., 'python3 main.py')")
                
                # 🧠 SMART PYTHON PATH REPLACER (Fix for -m flags & Arguments)
                if start_cmd.startswith("python3 ") or start_cmd.startswith("python "):
                    venv_python = os.path.join(folder_path, "venv", "bin", "python")
                    
                    # 'python3 -m bot' ko '/.../venv/bin/python -m bot' bana dega
                    if start_cmd.startswith("python3 "):
                        start_cmd = start_cmd.replace("python3 ", f"{venv_python} ", 1)
                    else:
                        start_cmd = start_cmd.replace("python ", f"{venv_python} ", 1)
                    
                    print(f"🔥 [PM2] Starting newly with Full VENV CMD: {start_cmd}")
                    
                    # Pura command single quotes mein dalenge taaki PM2 usko as a script command treat kare
                    cmd = f"pm2 start '{start_cmd}' --name {app_name}"
                    subprocess.run(cmd, shell=True, cwd=folder_path, check=True)
                else:
                    # Agar nodejs ya bash script ho
                    print(f"🔥 [PM2] Starting newly with CMD: {start_cmd}")
                    cmd = f"pm2 start '{start_cmd}' --name {app_name}"
                    subprocess.run(cmd, shell=True, cwd=folder_path, check=True)
                    
                print(f"✅ [PM2] {app_name} successfully started!")
                
            else:
                print(f"🔄 [PM2] Restarting existing bot: {app_name}...")
                subprocess.run(["pm2", "restart", app_name], check=True, capture_output=True)
                print(f"✅ [PM2] {app_name} successfully restarted!")
                
        return True
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if getattr(e, 'stderr', None) else str(e)
        print(f"❌ [DEPLOY ERROR]: {error_msg}")
        raise Exception(f"Deployment Failed: {error_msg}")
    except Exception as e:
        print(f"❌ [SYSTEM ERROR]: {str(e)}")
        raise Exception(f"Deployment System Error: {str(e)}")
        
