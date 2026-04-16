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
    print(f"🔍 [PM2] Checking if '{app_name}' already exists...")
    try:
        result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True)
        apps = json.loads(result.stdout)
        for app in apps:
            if app.get("name") == app_name:
                return True
        return False
    except Exception:
        return False

def stop_pm2(app_name: str):
    print(f"🛑 [PM2] Stopping bot: {app_name}...")
    try:
        subprocess.run(["pm2", "stop", app_name], check=False)
    except Exception:
        pass

def clear_pm2_logs(app_name: str):
    print(f"🧹 [PM2] Flushing logs for bot: {app_name}...")
    try:
        subprocess.run(["pm2", "flush", app_name], check=False)
        return True
    except Exception:
        return False

# ==========================================
# 2. SMART GIT ENGINE (Live Logging Enabled)
# ==========================================
def install_requirements(folder_path: str):
    venv_path = os.path.join(folder_path, "venv")
    pip_path = os.path.join(venv_path, "bin", "pip")
    log_file = os.path.join(folder_path, "build.log")
    
    if os.path.exists(os.path.join(folder_path, "requirements.txt")):
        append_log(folder_path, "📦 [PIP] Installing requirements into VENV...")
        with open(log_file, "a") as f:
            subprocess.run([pip_path, "install", "-r", "requirements.txt"], cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=True)
    else:
        append_log(folder_path, "⚠️ [PIP] No requirements.txt found. Skipping pip install.")

def pull_latest_code(repo_path: str, repo_url: str = None):
    if not os.path.exists(repo_path):
        os.makedirs(repo_path, exist_ok=True)

    log_file = os.path.join(repo_path, "build.log")
    
    # 🧹 Naya deploy hai, toh purana build log clear kar do
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("🚀 --- STARTING NEW BUILD ---\n")

    git_dir = os.path.join(repo_path, ".git")
    
    try:
        with open(log_file, "a") as f:
            if not os.path.exists(git_dir):
                if not repo_url: raise Exception("Repo URL missing for first-time setup!")
                append_log(repo_path, "🚀 [GIT] Initializing new repository...")
                subprocess.run(["git", "init"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                subprocess.run(["git", "remote", "add", "origin", repo_url], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                subprocess.run(["git", "fetch", "--all"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                try:
                    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                except:
                    subprocess.run(["git", "reset", "--hard", "origin/master"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
            else:
                append_log(repo_path, "📥 [GIT] Pulling latest updates...")
                if repo_url:
                    subprocess.run(["git", "remote", "set-url", "origin", repo_url], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                
                subprocess.run(["git", "fetch", "--all"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                
                append_log(repo_path, "🧹 [GIT] Sweeping local untracked changes safely...")
                # 🛡️ FIX: build.log ko bhi ignore karo warna delete ho jayega!
                subprocess.run(["git", "clean", "-fd", "-e", "venv", "-e", "data", "-e", "uploads", "-e", "database", "-e", "build.log"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True) 
                try:
                    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                except:
                    subprocess.run(["git", "reset", "--hard", "origin/master"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
        
        venv_path = os.path.join(repo_path, "venv")
        if not os.path.exists(venv_path):
            append_log(repo_path, "🏗️ [VENV] Creating Virtual Environment...")
            with open(log_file, "a") as f:
                subprocess.run(["python3", "-m", "venv", "venv"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)
        
        install_requirements(repo_path)
        return True
    except subprocess.CalledProcessError:
        append_log(repo_path, "❌ NEX_CLOUD_BUILD_FAILED")
        raise Exception("Code setup failed. Check live build logs.")
    except Exception as e:
        append_log(repo_path, f"❌ NEX_CLOUD_BUILD_FAILED: {str(e)}")
        raise Exception(f"Code setup failed: {str(e)}")

# ==========================================
# 3. MASTER DEPLOY ENGINE (Live Logging)
# ==========================================
def restart_pm2(app_name: str, folder_path: str, use_docker: bool = False, start_cmd: str = None):
    append_log(folder_path, f"\n🔄 [DEPLOY ENGINE] Initializing {app_name} (Docker: {use_docker})...")
    log_file = os.path.join(folder_path, "build.log")
    
    try:
        with open(log_file, "a") as f:
            if use_docker:
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
                                append_log(folder_path, f"🐍 [RUNTIME] Detected custom version: {python_base}")
                    except Exception as e:
                        append_log(folder_path, f"⚠️ [RUNTIME ERROR] Failed to read runtime.txt, using 3.10.")

                if not os.path.exists(dockerfile_path):
                    append_log(folder_path, f"🪄 [PPAM2] Auto-generating Public PM2 Dockerfile...")
                    auto_dockerfile = f"""FROM {python_base}\nENV DEBIAN_FRONTEND=noninteractive\nRUN apt-get update && apt-get install -y curl build-essential\nRUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs\nRUN npm install -g pm2\nWORKDIR /app\nCOPY . .\nRUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi\nRUN if [ -f package.json ]; then npm install; fi\nCMD ["pm2-runtime", "start", "bash", "--name", "{app_name}", "--", "-c", "{start_cmd}"]\n"""
                    with open(dockerfile_path, "w") as df:
                        df.write(auto_dockerfile)

                docker_app_name = app_name.lower()
                append_log(folder_path, f"🐳 [DOCKER] Building image... (This may take a few minutes)")
                subprocess.run(["docker", "build", "-t", docker_app_name, "."], cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                
                append_log(folder_path, f"🧹 [DOCKER] Removing old container...")
                subprocess.run(["docker", "stop", docker_app_name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=False)
                subprocess.run(["docker", "rm", docker_app_name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=False)
                
                append_log(folder_path, f"🚀 [DOCKER] Starting safe container...")
                subprocess.run([
                    "docker", "run", "-d", "--name", docker_app_name, 
                    "--memory=1g", "--cpus=1.0", "--restart=unless-stopped", docker_app_name
                ], stdout=f, stderr=subprocess.STDOUT, check=True)
                
            else:
                is_running = check_pm2_exists(app_name)
                if not is_running:
                    if not start_cmd: raise Exception("❌ PM2 ke liye start_cmd zaroori hai!")
                    parts = start_cmd.split()
                    if parts and parts[0] in ["python", "python3"]:
                        venv_python = os.path.join(folder_path, "venv", "bin", "python")
                        parts[0] = venv_python
                        start_cmd = " ".join(parts)
                    
                    append_log(folder_path, f"🔥 [PM2] Executing VIP CMD: {start_cmd}")
                    subprocess.run(["pm2", "start", "bash", "--name", app_name, "--", "-c", start_cmd], cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=True)
                else:
                    append_log(folder_path, f"🔄 [PM2] Restarting existing bot...")
                    subprocess.run(["pm2", "restart", app_name], stdout=f, stderr=subprocess.STDOUT, check=True)

            # 🔥 SMART STOP: Ye word aate hi frontend ka websocket disconnect ho jayega!
            append_log(folder_path, f"✅ NEX_CLOUD_BUILD_COMPLETE")
            return True
            
    except subprocess.CalledProcessError:
        append_log(folder_path, "❌ NEX_CLOUD_BUILD_FAILED")
        raise Exception("Deployment Failed. Check build logs.")
    except Exception as e:
        append_log(folder_path, f"❌ NEX_CLOUD_BUILD_FAILED")
        raise Exception(f"System Error: {str(e)}")
                    
