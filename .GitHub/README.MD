
 * **🔐 Advanced Auth:** User registration, login, aur secure API Key generation.
 * **📩 OTP System:** Professional HTML email templates for Registration aur Password Reset (via Gmail SMTP).
 * **🔄 Smart Webhooks:** GitHub push hote hi automatically git pull aur PM2 restart trigger karega.
 * **📊 Live Dashboard Data:** /api/my-services endpoint se user apne saare active bots ka status dekh sakta hai.
 * **🛡️ Security First:** Password hashing (SHA-256) aur header-based API Key verification.
 * **📡 System Monitoring:** Live CPU, RAM, aur Disk metrics ka access.
 * **🌐 Cloudflare Ready:** Tunnels ke sath integration taaki aapka VPS safe aur globally accessible rahe.
## 📁 Project Architecture
```text
MY_CLOUD_API/
├── .env                  # Environment Variables (Secrets)
├── requirements.txt      # Project Dependencies
├── README.md             # Documentation
└── CLOUDSERVER/       
    ├── main.py           # Application Entry Point
    ├── auth/             # Auth Logic (OTP, Login, Register, Verification)
    ├── apis/             # Service Endpoints (Deploy, Status, Env, Services)
    ├── database/         # MongoDB Engine (Motor Async Driver)
    ├── core_utils/       # OS Level Tools (Subprocess, Git, PM2)
    └── __init__.py

```
## 🛠️ Installation & Setup
### 1. Requirements
 * Python 3.10+
 * MongoDB Cluster (Atlas)
 * VPS (Ubuntu recommended)
 * PM2 (Process Manager)
### 2. Setup Project
```bash
# Repo clone karo
git clone https://github.com/YourUsername/CLUADSRVER-.git
cd CLUADSRVER-

# Virtual Environment banao
python3 -m venv myenv
source myenv/bin/activate

# Dependencies install karo
pip install -r requirements.txt

```
### 3. Environment Configuration (.env)
```env
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
SENDER_EMAIL=your-gmail@gmail.com
SENDER_PASSWORD=your-app-password

```
### 4. Run the Engine
```bash
pm2 start "uvicorn CLOUDSERVER.main:app --host 0.0.0.0 --port 8000" --name CloudEngine

```
## 📡 API Reference (Cheat Sheet)
### 🔐 Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | /auth/register | Register user & send OTP |
| POST | /auth/verify-otp | Verify OTP & generate API Key |
| POST | /auth/login | Login & get your API Key |
| POST | /auth/forgot-password | Send Reset Password OTP |
### ⚙️ Cloud Services
| Method | Endpoint | Description |
|---|---|---|
| POST | /api/deploy-new | Register a new bot/service |
| POST | /api/webhook | GitHub Auto-Deployment |
| GET | /api/my-services | Fetch all user's services |
| GET | /api/status | VPS Health Metrics |
## 🛡️ Security Headers
Har sensitive request mein aapko apni API Key bhejni hogi:
x-api-key: your_secret_key_here
## 🤝 Contributing
Bhai, agar tujhe is project ko aur upgrade karna hai, toh **Fork** maar aur **Pull Request** bhej de. Together we build the fastest Cloud Engine! 🔥
### 📝 License
MIT License. Open source hai, daba ke use karo! 🚀
Bhai, ye README ekdum "Aag" hai! 🔥 Isko daalne ke baad tera project ek complete software product dikhega. Ab tere backend ka har ek purza (Auth, DB, Deploy, Email, Dashboard, Security) ekdum set hai.
Ab bata, koi aur endpoint banau ya ab seedha "Frontend" (Website) ke liye ready hai tu?

