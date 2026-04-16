import subprocess
import os
import json

# ==========================================
# 📝 LIVE BUILD LOG ENGINE (RENDER STYLE)
# ==========================================
def append_log(folder_path: str, message: str):
    """Console pe bhi print karega aur build.log mein bhi daalega live stream ke liye"""
    print(message)
    os.makedirs(folder_path, exist_ok=True)
    log_file = os.path.join(folder_path, "build.log")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass

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
    """VENV ke andar specific requirements install karne ke liye (SNIPER MODE)"""
    venv_path = os.path.join(folder_path, "venv")
    pip_path = os.path.join(venv_path, "bin", "pip")
    log_file = os.path.join(folder_path, "build.log")
    req_file = os.path.join(folder_path, "requirements.txt")
    
    # 🔥 FIX: Ensure VENV exists before installing (Sirf VIP PM2 ke liye chalega)
    if not os.path.exists(venv_path):
        append_log(folder_path, "🏗️ [VENV] Creating isolated Virtual Environment for PM2 Engine...")
        with open(log_file, "a", encoding="utf-8") as f:
            subprocess.run(["python3", "-m", "venv", "venv"], cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=True)

    if os.path.exists(req_file):
        with open(log_file, "a", encoding="utf-8") as f:
            append_log(folder_path, "⬆️ [PIP] Upgrading PIP to latest version to prevent conflicts...")
            subprocess.run([pip_path, "install", "--upgrade", "pip"], cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=False)
            
            append_log(folder_path, "🔫 [PIP] SNIPER MODE ON: Installing requirements ONE-BY-ONE to kill Dependency Hell...")
            with open(req_file, "r", encoding="utf-8") as reqs:
                for line in reqs:
                    pkg = line.strip()
                    if pkg and not pkg.startswith("#"):
                        append_log(folder_path, f"⬇️ Installing: {pkg}")
                        subprocess.run([pip_path, "install", "--no-cache-dir", pkg], cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=False)
            
            append_log(folder_path, "✅ [PIP] All packages installed successfully via Sniper Mode!")
    else:
        append_log(folder_path, "⚠️ [PIP] No requirements.txt found. Skipping pip install.")

def pull_latest_code(repo_path: str, repo_url: str = None):
    """Smart Clone/Pull & Auto-VENV with GUNDA FORCE PULL"""
    if not os.path.exists(repo_path):
        os.makedirs(repo_path, exist_ok=True)

    log_file = os.path.join(repo_path, "build.log")
    
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("🚀 --- STARTING NEW BUILD ---\n")

    git_dir = os.path.join(repo_path, ".git")
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            if not os.path.exists(git_dir):
                if not repo_url:
                    raise Exception("Repo URL missing for first-time setup!")
                
                append_log(repo_path, "🚀 [GIT] First time setup. Initializing repo...")
                subprocess.run(["git", "init"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                subprocess.run(["git", "fetch", "--all"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                
                try:
                    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                except:
                    subprocess.run(["git", "reset", "--hard", "origin/master"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
            else:
                append_log(repo_path, "📥 [GIT] Updating existing code in repository...")
                if repo_url:
                    subprocess.run(["git", "remote", "set-url", "origin", repo_url], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                
                subprocess.run(["git", "fetch", "--all"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                
                append_log(repo_path, "🧹 [GIT] Sweeping local untracked changes safely...")
                subprocess.run(["git", "clean", "-fd", "-e", "venv", "-e", "data", "-e", "uploads", "-e", "database", "-e", "build.log"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True) 
                
                try:
                    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                except:
                    subprocess.run(["git", "reset", "--hard", "origin/master"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
        
        # 🔥 BUG FIX: Yahan se install_requirements HATA diya gaya hai! 
        # (Sirf restart_pm2 mein VIP engine block mein chalega)
        return True
    except subprocess.CalledProcessError:
        append_log(repo_path, "❌ NEX_CLOUD_BUILD_FAILED")
        raise Exception("Code setup failed. Check live build logs.")
    except Exception as e:
        append_log(repo_path, f"❌ NEX_CLOUD_BUILD_FAILED")
        raise Exception(f"Code setup failed: {str(e)}")

# ==========================================
# 3. MASTER DEPLOY ENGINE (PPAM2 + VIP PM2 + Logging)
# ==========================================
def restart_pm2(app_name: str, folder_path: str, use_docker: bool = False, start_cmd: str = None):
    append_log(folder_path, f"🔄 [DEPLOY ENGINE] Processing bot: {app_name} (Docker Mode: {use_docker})...")
    log_file = os.path.join(folder_path, "build.log")
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            if use_docker:
                docker_app_name = app_name.lower()
                
                dockerignore_path = os.path.join(folder_path, ".dockerignore")
                if not os.path.exists(dockerignore_path):
                    dockerignore_content = ".git\nvenv\n__pycache__\n*.session\n*.session-journal\nlogs\nnode_modules\nbuild.log\n"
                    with open(dockerignore_path, "w") as di_file:
                        di_file.write(dockerignore_content)
                    append_log(folder_path, "🛡️ [DOCKER] Generated .dockerignore to speed up build!")

                append_log(folder_path, f"🧹 [DOCKER] Hunting down Ghost Containers for {docker_app_name}...")
                subprocess.run(["docker", "rm", "-f", docker_app_name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=False)

                dockerfile_path = os.path.join(folder_path, "Dockerfile")
                runtime_path = os.path.join(folder_path, "runtime.txt")
                
                python_base = "python:3.10-slim" 
                
                if os.path.exists(runtime_path):
                    try:
                        with open(runtime_path, "r") as rt:
                            runtime_content = rt.read().strip().lower()
                            if runtime_content.startswith("python-"):
                                version = runtime_content.split("-")[1]
                                major_minor = ".".join(version.split(".")[:2])
                                python_base = f"python:{major_minor}-slim"
                                append_log(folder_path, f"🐍 [RUNTIME DETECTED] Using specific Python version: {python_base}")
                    except Exception as e:
                        append_log(folder_path, f"⚠️ [RUNTIME ERROR] Failed to read runtime.txt, using default 3.10.")

                if not os.path.exists(dockerfile_path):
                    append_log(folder_path, f"🪄 [PPAM2] Dockerfile not found! Auto-generating Public PM2 container for {python_base}...")
                    auto_dockerfile = f"""FROM {python_base}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y git curl build-essential ffmpeg aria2
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs
RUN npm install -g pm2
WORKDIR /app
COPY . .
RUN if [ -f requirements.txt ]; then \
        python3 -m pip install --upgrade pip && \
        tr -d '\\r' < requirements.txt | grep -v '^#' | xargs -n 1 pip install --no-cache-dir; \
    fi
RUN if [ -f package.json ]; then npm install; fi
CMD ["pm2-runtime", "start", "bash", "--name", "{app_name}", "--", "-c", "{start_cmd}"]
"""
                    with open(dockerfile_path, "w") as df:
                        df.write(auto_dockerfile)
                else:
                    append_log(folder_path, f"📄 [DOCKER] Existing Dockerfile detected. Using repository's Dockerfile.")

                append_log(folder_path, f"🐳 [DOCKER] Building image for {docker_app_name}... (Takes time)")
                subprocess.run(["docker", "build", "-t", docker_app_name, "."], cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                
                append_log(folder_path, f"🚀 [DOCKER] Running PPAM2 container for {docker_app_name} with Limits...")
                subprocess.run([
                    "docker", "run", "-d", 
                    "--name", docker_app_name, 
                    "--memory=1g",       
                    "--cpus=1.0",        
                    "--restart=unless-stopped",
                    docker_app_name
                ], stdout=f, stderr=subprocess.STDOUT, check=True)
                append_log(folder_path, f"✅ [DOCKER] {docker_app_name} successfully deployed using PPAM2 Engine!")
                
            else:
                # 👑 THE "VIP PM2" ENGINE 👑
                # 🔥 FIX: Sirf jab VIP PM2 engine chuna jayega, tabhi requirements install hongi (host server pe)
                append_log(folder_path, "⚙️ [PM2] Preparing VIP PM2 Environment...")
                install_requirements(folder_path)
                
                is_running = check_pm2_exists(app_name)
                
                if not is_running:
                    if not start_cmd:
                        raise Exception("❌ PM2 ke liye start_cmd zaroori hai!")
                    
                    parts = start_cmd.split()
                    if parts and parts[0] in ["python", "python3"]:
                        venv_python = os.path.join(folder_path, "venv", "bin", "python")
                        parts[0] = venv_python
                        start_cmd = " ".join(parts)
                    
                    append_log(folder_path, f"🔥 [PM2] Starting VIP newly with CMD: {start_cmd}")
                    
                    subprocess.run([
                        "pm2", "start", "bash", 
                        "--name", app_name, 
                        "--", "-c", start_cmd
                    ], cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                        
                    append_log(folder_path, f"✅ [PM2] {app_name} successfully started!")
                    
                else:
                    append_log(folder_path, f"🔄 [PM2] Restarting existing bot: {app_name}...")
                    subprocess.run(["pm2", "restart", app_name], stdout=f, stderr=subprocess.STDOUT, check=True)
                    append_log(folder_path, f"✅ [PM2] {app_name} successfully restarted!")

            append_log(folder_path, f"✅ NEX_CLOUD_BUILD_COMPLETE")
            return True
            
    except subprocess.CalledProcessError:
        append_log(folder_path, "❌ NEX_CLOUD_BUILD_FAILED")
        raise Exception("Deployment Failed. Check build logs.")
    except Exception as e:
        append_log(folder_path, f"❌ NEX_CLOUD_BUILD_FAILED")
        raise Exception(f"Deployment System Error: {str(e)}")
        
