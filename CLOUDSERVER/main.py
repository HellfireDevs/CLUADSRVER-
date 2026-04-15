from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ==========================================
# 📦 IMPORTING ALL ROUTERS & MODULES
# ==========================================
from CLOUDSERVER.auth import auth_api
from CLOUDSERVER.apis import (
    deploy, restart, status, ping, 
    envmanager, services, logs,  
    payment, github, account, support,
    google_auth  # 🔥 NAYA: Google Auth Import
)

app = FastAPI(
    title="NEX CLOUD Engine ☁️",
    description="Custom deployment API with MongoDB, GitHub OAuth, Google Login, and Support System! 🔥",
    version="2.6.0",     # Version upgraded for Google OAuth 😎
    docs_url="/docs",    
    redoc_url="/redoc"
)

# ==========================================
# 🛡️ CORS SETUP
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🔗 API ROUTERS (Linking everything)
# ==========================================

# 1. Authentication & Security
app.include_router(auth_api.router, prefix="/auth", tags=["Authentication & Security"])

# 2. Core Server & Bot APIs
app.include_router(deploy.router, prefix="/api", tags=["Deployment & Webhooks"])
app.include_router(restart.router, prefix="/api", tags=["Process Management"])
app.include_router(status.router, prefix="/api", tags=["System Status"])
app.include_router(ping.router, prefix="/api", tags=["Health & Uptime"])
app.include_router(envmanager.router, prefix="/api", tags=["Environment Variables & Repo Updates"])

# 3. User Dashboard & Profile Data
app.include_router(services.router, prefix="/api", tags=["User Dashboard"])

# 4. WebSockets (Live Logs)
app.include_router(logs.router, prefix="/ws", tags=["Live Logs Streaming"])

# 5. Billing, Payments & Webhooks (Telegram Bot Magic) 💸
app.include_router(payment.router, prefix="/api", tags=["Billing & Payments"])

# 6. GitHub Integration (OAuth & Private Repos) 🐙
app.include_router(github.router, prefix="/api", tags=["GitHub Connect"])

# 7. Google Login (OAuth) 🔴
app.include_router(google_auth.router, prefix="/api/google", tags=["Google OAuth"])

# 8. Account Management (Delete with OTP) 💣
app.include_router(account.router, prefix="/api/account", tags=["Account Management"])

# 9. Support Desk (Ticket System) 🎫
app.include_router(support.router, prefix="/api/support", tags=["Support Desk"])


# ==========================================
# 🚀 ROOT ENDPOINT (Health Check)
# ==========================================
@app.get("/", tags=["Root"])
async def root_check():
    return {
        "status": "success",
        "message": "🚀 Welcome to NEX CLOUD Engine!",
        "engine_state": "Online & Running",
        "database": "MongoDB Connected",
        "version": "2.6.0",
        "tip": "Visit /docs to test the APIs."
    }
    
