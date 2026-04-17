import subprocess
import os
import json
from datetime import datetime

# ==========================================
# 📝 LIVE BUILD LOG ENGINE (RENDER STYLE)
# ==========================================
def append_log(folder_path: str, message: str):
    """Console pe bhi print karega aur build.log mein bhi daalega live stream ke liye"""
    ts = datetime.now().strftime("%H:%M:%S")
    stamped = f"[{ts}] {message}"
    print(stamped)
    os.makedirs(folder_path, exist_ok=True)
    log_file = os.path.join(folder_path, "build.log")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(stamped + "\n")
    except Exception:
        pass


# ==========================================
# 🔧 HELPER: Auto-detect active branch
# ==========================================
def get_active_branch(repo_path: str) -> str:
    """
    Remote pe jo branch exist kare usse return karta hai.
    'main' ko priority deta hai, fallback 'master' pe.
    """
    for branch in ["main", "master"]:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch],
            cwd=repo_path, capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return branch
    return "main"  # last resort default


# ==========================================
# 1. PM2 & DOCKER OPERATIONS
# ==========================================
def check_pm2_exists(app_name: str) -> bool:
    """Check karega ki PM2 mein ye naam pehle se toh nahi chal raha"""
    print(f"🔍 [PM2] Checking if '{app_name}' already exists...")
    try:
        result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True)
        raw = result.stdout.strip()
        if not raw:
            return False
        apps = json.loads(raw)
        for app in apps:
            if app.get("name") == app_name:
                print(f"⚠️ [PM2] App '{app_name}' pehle se exist karta hai!")
                return True
        print(f"✅ [PM2] App '{app_name}' available hai.")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ [PM2 CHECK] JSON parse failed: {e}")
        return False
    except Exception as e:
        print(f"❌ [PM2 CHECK ERROR]: {e}")
        return False


def stop_pm2(app_name: str, use_docker: bool = False):
    """Dashboard se bot ko stop karne ke liye"""
    print(f"🛑 Stopping bot: {app_name} (Docker: {use_docker})...")
    try:
        if use_docker:
            subprocess.run(["docker", "stop", app_name.lower()], check=False)
            print(f"✅ [DOCKER] {app_name} stopped.")
        else:
            subprocess.run(["pm2", "stop", app_name], check=False)
            print(f"✅ [PM2] {app_name} stopped.")
    except Exception as e:
        print(f"❌ [STOP ERROR]: {e}")


def quick_restart(app_name: str, use_docker: bool = False):
    """Direct restart button dabane par turant restart karega"""
    print(f"🔄 Quick Restarting bot: {app_name} (Docker: {use_docker})...")
    try:
        if use_docker:
            subprocess.run(["docker", "restart", app_name.lower()], check=False)
            print(f"✅ [DOCKER] {app_name} restarted.")
        else:
            subprocess.run(["pm2", "restart", app_name], check=False)
            print(f"✅ [PM2] {app_name} restarted.")
    except Exception as e:
        print(f"❌ [RESTART ERROR]: {e}")


def clear_pm2_logs(app_name: str):
    """PM2 ke logs clear karne ke liye (Flush)"""
    print(f"🧹 [PM2] Flushing logs for bot: {app_name}...")
    try:
        subprocess.run(["pm2", "flush", app_name], check=False)
        print(f"✅ [PM2] Logs cleared for {app_name}.")
        return True
    except Exception as e:
        print(f"❌ [PM2 FLUSH ERROR]: {e}")
        return False


# ==========================================
# 2. SMART GIT ENGINE
# ==========================================
def install_requirements(folder_path: str):
    """VENV ke andar requirements install karne ke liye (SNIPER MODE)"""
    venv_path = os.path.join(folder_path, "venv")
    pip_path = os.path.join(venv_path, "bin", "pip")
    log_file = os.path.join(folder_path, "build.log")
    req_file = os.path.join(folder_path, "requirements.txt")

    if not os.path.exists(venv_path):
        append_log(folder_path, "🏗️ [VENV] Creating isolated Virtual Environment...")
        result = subprocess.run(
            ["python3", "-m", "venv", "venv"],
            cwd=folder_path, capture_output=True, text=True
        )
        if result.returncode != 0:
            append_log(folder_path, f"❌ [VENV] Creation failed:\n{result.stderr}")
            raise Exception("VENV creation failed.")

    if not os.path.exists(req_file):
        append_log(folder_path, "⚠️ [PIP] No requirements.txt found. Skipping pip install.")
        return

    with open(log_file, "a", encoding="utf-8") as f:
        append_log(folder_path, "⬆️ [PIP] Upgrading PIP...")
        subprocess.run(
            [pip_path, "install", "--upgrade", "pip"],
            cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=False
        )

        append_log(folder_path, "🔫 [PIP] SNIPER MODE: Installing packages one-by-one...")
        failed_pkgs = []
        with open(req_file, "r", encoding="utf-8") as reqs:
            for line in reqs:
                pkg = line.strip()
                if not pkg or pkg.startswith("#"):
                    continue
                append_log(folder_path, f"⬇️ Installing: {pkg}")
                res = subprocess.run(
                    [pip_path, "install", "--no-cache-dir", pkg],
                    cwd=folder_path, stdout=f, stderr=subprocess.STDOUT
                )
                if res.returncode != 0:
                    failed_pkgs.append(pkg)

        if failed_pkgs:
            append_log(folder_path, f"⚠️ [PIP] Failed packages: {', '.join(failed_pkgs)}")
        else:
            append_log(folder_path, "✅ [PIP] All packages installed via Sniper Mode!")


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

                branch = get_active_branch(repo_path)
                append_log(repo_path, f"🌿 [GIT] Using branch: {branch}")
                subprocess.run(["git", "reset", "--hard", f"origin/{branch}"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)

            else:
                append_log(repo_path, "📥 [GIT] Updating existing repository...")
                if repo_url:
                    subprocess.run(["git", "remote", "set-url", "origin", repo_url], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)

                subprocess.run(["git", "fetch", "--all"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)

                append_log(repo_path, "🧹 [GIT] Cleaning untracked files (venv/data/uploads safe)...")
                subprocess.run(
                    ["git", "clean", "-fd", "-e", "venv", "-e", "data", "-e", "uploads", "-e", "database", "-e", "build.log"],
                    cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True
                )

                branch = get_active_branch(repo_path)
                append_log(repo_path, f"🌿 [GIT] Using branch: {branch}")
                subprocess.run(["git", "reset", "--hard", f"origin/{branch}"], cwd=repo_path, stdout=f, stderr=subprocess.STDOUT, check=True)

        return True

    except subprocess.CalledProcessError as e:
        append_log(repo_path, f"❌ NEX_CLOUD_BUILD_FAILED (git error: {e})")
        raise Exception("Code setup failed. Check live build logs.")
    except Exception as e:
        append_log(repo_path, f"❌ NEX_CLOUD_BUILD_FAILED: {e}")
        raise Exception(f"Code setup failed: {e}")


# ==========================================
# 3. MASTER DEPLOY ENGINE
# ==========================================
def restart_pm2(app_name: str, folder_path: str, use_docker: bool = False, start_cmd: str = None):
    append_log(folder_path, f"🔄 [DEPLOY ENGINE] Processing: {app_name} (Docker: {use_docker})...")
    log_file = os.path.join(folder_path, "build.log")

    try:
        with open(log_file, "a", encoding="utf-8") as f:
            if use_docker:
                docker_app_name = app_name.lower()

                # 🧹 1. SMART DOCKERIGNORE
                dockerignore_path = os.path.join(folder_path, ".dockerignore")
                if not os.path.exists(dockerignore_path):
                    content = ".git\nvenv\n__pycache__\n*.session\n*.session-journal\nlogs\nnode_modules\nbuild.log\n"
                    with open(dockerignore_path, "w") as di:
                        di.write(content)
                    append_log(folder_path, "🛡️ [DOCKER] Generated .dockerignore to speed up build!")

                # 👻 2. GHOST CONTAINER KILLER
                append_log(folder_path, f"🧹 [DOCKER] Removing old container: {docker_app_name}...")
                subprocess.run(["docker", "rm", "-f", docker_app_name],
                               stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=False)

                # 🏗️ 3. DOCKERFILE LOGIC
                dockerfile_path = os.path.join(folder_path, "Dockerfile")
                runtime_path = os.path.join(folder_path, "runtime.txt")
                python_base = "python:3.10-slim"

                if os.path.exists(runtime_path):
                    try:
                        with open(runtime_path, "r") as rt:
                            content = rt.read().strip().lower()
                            if content.startswith("python-"):
                                version = content.split("-")[1]
                                major_minor = ".".join(version.split(".")[:2])
                                python_base = f"python:{major_minor}-slim"
                                append_log(folder_path, f"🐍 [RUNTIME] Using Python: {python_base}")
                    except Exception as e:
                        append_log(folder_path, f"⚠️ [RUNTIME] Could not read runtime.txt: {e}. Using default 3.10.")

                if not os.path.exists(dockerfile_path):
                    append_log(folder_path, f"🪄 [PPAM2] Auto-generating Dockerfile for {python_base}...")
                    auto_dockerfile = f"""FROM {python_base}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y git curl build-essential ffmpeg aria2
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs
RUN npm install -g pm2
WORKDIR /app
COPY . .
RUN if [ -f requirements.txt ]; then \\
        python3 -m pip install --upgrade pip && \\
        tr -d '\\r' < requirements.txt | grep -v '^#' | xargs -n 1 pip install --no-cache-dir; \\
    fi
RUN if [ -f package.json ]; then npm install; fi
CMD ["pm2-runtime", "start", "bash", "--name", "{app_name}", "--", "-c", "{start_cmd}"]
"""
                    with open(dockerfile_path, "w") as df:
                        df.write(auto_dockerfile)
                else:
                    append_log(folder_path, "📄 [DOCKER] Using repo's existing Dockerfile.")

                # 🚀 4. BUILD & RUN
                append_log(folder_path, f"🐳 [DOCKER] Building image: {docker_app_name}...")
                subprocess.run(["docker", "build", "-t", docker_app_name, "."],
                               cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=True)

                append_log(folder_path, f"🚀 [DOCKER] Running container: {docker_app_name}...")
                docker_run_cmd = [
                    "docker", "run", "-d",
                    "--name", docker_app_name,
                    "--memory=1g",
                    "--cpus=1.0",
                    "--restart=unless-stopped"
                ]

                env_path = os.path.join(folder_path, ".env")
                if os.path.exists(env_path):
                    append_log(folder_path, "🔗 [DOCKER] Mounting .env for live updates...")
                    docker_run_cmd.extend(["-v", f"{env_path}:/app/.env"])

                docker_run_cmd.append(docker_app_name)
                subprocess.run(docker_run_cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
                append_log(folder_path, f"✅ [DOCKER] {docker_app_name} deployed via PPAM2!")

            else:
                # 👑 VIP PM2 ENGINE
                append_log(folder_path, "⚙️ [PM2] Preparing VIP PM2 environment...")
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

                    append_log(folder_path, f"🔥 [PM2] Starting: {app_name} → {start_cmd}")
                    subprocess.run([
                        "pm2", "start", "bash",
                        "--name", app_name,
                        "--", "-c", start_cmd
                    ], cwd=folder_path, stdout=f, stderr=subprocess.STDOUT, check=True)

                    # 💾 Save PM2 list so bots survive server reboot
                    subprocess.run(["pm2", "save"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    append_log(folder_path, f"✅ [PM2] {app_name} started & saved!")

                else:
                    append_log(folder_path, f"🔄 [PM2] Restarting existing: {app_name}...")
                    subprocess.run(["pm2", "restart", app_name],
                                   stdout=f, stderr=subprocess.STDOUT, check=True)
                    append_log(folder_path, f"✅ [PM2] {app_name} restarted!")

        append_log(folder_path, "✅ NEX_CLOUD_BUILD_COMPLETE")
        return True

    except subprocess.CalledProcessError as e:
        append_log(folder_path, f"❌ NEX_CLOUD_BUILD_FAILED (process error: {e})")
        raise Exception("Deployment Failed. Check build logs.")
    except Exception as e:
        append_log(folder_path, f"❌ NEX_CLOUD_BUILD_FAILED: {e}")
        raise Exception(f"Deployment System Error: {e}")
        
