import subprocess
import os
import json

# ==========================================
# 1. PM2 OPERATIONS (Check, Stop, Flush)
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

def clear_pm2_logs(app_name: str):
    """PM2 ke logs clear karne ke liye (Flush) taaki server fast rahe"""
    print(f"🧹 [PM2] Flushing logs for bot: {app_name}...")
    try:
        subprocess.run(["pm2", "flush", app_name], check=False)
        print(f"✅ [PM2] Logs cleared successfully for {app_name}.")
        return True
    except Exception as e:
        print(f"❌ [PM2 FLUSH ERROR]: {str(e)}")
        return False

# ==========================================
# 2. SMART GIT ENGINE (Init + Fetch + Reset + Clean + VENV)
# ==========================================
def install_requirements(folder_path: str):
    """VENV ke andar specific requirements install karne ke liye"""
    venv_path = os.path.join(folder_path, "venv")
    pip_path = os.path.join(venv_path, "bin", "pip")
    
    if os.path.exists(os.path.join(folder_path, "requirements.txt")):
        print("📦 [PIP] Installing/Updating requirements into isolated VENV...")
        subprocess.run([pip_path, "install", "-r", "requirements.txt"], cwd=folder_path, check=True)
    else:
        print("⚠️ [PIP] No requirements.txt found. Skipping pip install.")

def pull_latest_code(repo_path: str, repo_url: str = None):
    """Smart Clone/Pull & Auto-VENV with GUNDA FORCE PULL"""
    if not os.path.exists(repo_path):
        os.makedirs(repo_path, exist_ok=True)

    git_dir = os.path.join(repo_path, ".git")
    
    try:
        if not os.path.exists(git_dir):
            if not repo_url:
                raise Exception("Repo URL missing for first-time setup!")
            
            print(f"🚀 [GIT] First time setup. Initializing repo...")
            subprocess.run(["git", "init"], cwd=repo_path, check=True)
            subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=repo_path, check=True)
            subprocess.run(["git", "fetch", "--all"], cwd=repo_path, check=True)
            
            try:
                subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, check=True)
            except:
                subprocess.run(["git", "reset", "--hard", "origin/master"], cwd=repo_path, check=True)
        else:
            print(f"📥 [GIT] Updating existing code in {repo_path}...")
            if repo_url:
                subprocess.run(["git", "remote", "set-url", "origin", repo_url], cwd=repo_path, check=True)
            
            subprocess.run(["git", "fetch", "--all"], cwd=repo_path, check=True)
            
            # 💣 FIX: Clean karte waqt venv, data aur uploads ko ignore karo!
            print(f"🧹 [GIT] Sweeping local untracked changes safely...")
            subprocess.run(["git", "clean", "-fd", "-e", "venv", "-e", "data", "-e", "uploads", "-e", "database"], cwd=repo_path, check=True) 
            
            try:
                subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, check=True)
            except:
                subprocess.run(["git", "reset", "--hard", "origin/master"], cwd=repo_path, check=True)
        
        venv_path = os.path.join(repo_path, "venv")
        if not os.path.exists(venv_path):
            subprocess.run(["python3", "-m", "venv", "venv"], cwd=repo_path, check=True)
        
        install_requirements(repo_path)
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if getattr(e, 'stderr', None) else str(e)
        raise Exception(f"Code setup failed: {error_msg}")
    except Exception as e:
        raise Exception(f"Code setup failed: {str(e)}")

# ==========================================
# 3. MASTER DEPLOY ENGINE (PPAM2 + VIP PM2)
# ==========================================
def restart_pm2(app_name: str, folder_path: str, use_docker: bool = False, start_cmd: str = None):
    print(f"🔄 [DEPLOY ENGINE] Processing bot: {app_name} (Docker Mode: {use_docker})...")
    
    try:
        if use_docker:
            dockerfile_path = os.path.join(folder_path, "Dockerfile")
            runtime_path = os.path.join(folder_path, "runtime.txt")
            
            # 🔥 SMART RUNTIME ENGINE (Heroku Style)
            python_base = "python:3.10-slim" 
            
            if os.path.exists(runtime_path):
                try:
                    with open(runtime_path, "r") as f:
                        runtime_content = f.read().strip().lower()
                        if runtime_content.startswith("python-"):
                            version = runtime_content.split("-")[1]
                            major_minor = ".".join(version.split(".")[:2])
                            python_base = f"python:{major_minor}-slim"
                            print(f"🐍 [RUNTIME DETECTED] Using specific Python version: {python_base}")
                except Exception as e:
                    print(f"⚠️ [RUNTIME ERROR] Failed to read runtime.txt, using default 3.10. Error: {e}")

            # 🪄 PPAM2 AUTO-DOCKERFILE ENGINE
            if not os.path.exists(dockerfile_path):
                print(f"🪄 [PPAM2] Dockerfile not found! Auto-generating Public PM2 container for {python_base}...")
                auto_dockerfile = f"""FROM {python_base}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y curl build-essential
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs
RUN npm install -g pm2
WORKDIR /app
COPY . .
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN if [ -f package.json ]; then npm install; fi
# Running via PM2-Runtime inside Docker
CMD ["pm2-runtime", "start", "bash", "--name", "{app_name}", "--", "-c", "{start_cmd}"]
"""
                with open(dockerfile_path, "w") as f:
                    f.write(auto_dockerfile)

            docker_app_name = app_name.lower()
            print(f"🐳 [DOCKER] Building image for {docker_app_name}...")
            subprocess.run(["docker", "build", "-t", docker_app_name, "."], cwd=folder_path, check=True)
            
            print(f"🧹 [DOCKER] Cleaning up old container (if exists)...")
            subprocess.run(["docker", "stop", docker_app_name], stderr=subprocess.DEVNULL, check=False)
            subprocess.run(["docker", "rm", docker_app_name], stderr=subprocess.DEVNULL, check=False)
            
            print(f"🚀 [DOCKER] Running PPAM2 container for {docker_app_name} with Limits...")
            subprocess.run([
                "docker", "run", "-d", 
                "--name", docker_app_name, 
                "--memory=1g",       
                "--cpus=1.0",        
                "--restart=unless-stopped",
                docker_app_name
            ], check=True)
            print(f"✅ [DOCKER] {docker_app_name} successfully deployed using PPAM2 Engine!")
            
        else:
            # 👑 THE "VIP PM2" ENGINE 👑
            is_running = check_pm2_exists(app_name)
            
            if not is_running:
                if not start_cmd:
                    raise Exception("❌ PM2 ke liye start_cmd zaroori hai!")
                
                # 🛡️ FIX 1: Split() Logic for VENV
                parts = start_cmd.split()
                if parts and parts[0] in ["python", "python3"]:
                    venv_python = os.path.join(folder_path, "venv", "bin", "python")
                    parts[0] = venv_python
                    start_cmd = " ".join(parts)
                
                print(f"🔥 [PM2] Starting VIP newly with CMD: {start_cmd}")
                
                # 🛡️ FIX 2: bash -c wrapper (Prevents script misinterpretation & avoids shell=True)
                subprocess.run([
                    "pm2", "start", "bash", 
                    "--name", app_name, 
                    "--", "-c", start_cmd
                ], cwd=folder_path, check=True)
                    
                print(f"✅ [PM2] {app_name} successfully started!")
                
            else:
                print(f"🔄 [PM2] Restarting existing bot: {app_name}...")
                subprocess.run(["pm2", "restart", app_name], check=True, capture_output=True)
                print(f"✅ [PM2] {app_name} successfully restarted!")
                
        return True
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if getattr(e, 'stderr', None) else str(e)
        raise Exception(f"Deployment Failed: {error_msg}")
    except Exception as e:
        raise Exception(f"Deployment System Error: {str(e)}")
        
