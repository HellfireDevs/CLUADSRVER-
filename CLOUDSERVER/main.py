from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ==========================================
# 📦 IMPORTING ALL ROUTERS & MODULES
# ==========================================
from CLOUDSERVER.auth import auth_api
from CLOUDSERVER.apis import deploy, restart, status, ping, env_manager, services

# Note: Jaise hi app start hoga, database connection file (database.py) 
# background mein apne aap trigger ho jayegi in imports ke through!

app = FastAPI(
    title="My Custom Cloud API ☁️",
    description="Render aur Heroku se bhi fast custom deployment API with MongoDB! 🔥",
    version="2.0.0",     # Version upgrade kar diya 😎
    docs_url="/docs",    # Yahan se tu bina website ke API test karega
    redoc_url="/redoc"
)

# ==========================================
# 🛡️ CORS SETUP
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Abhi sabko allow kiya hai, baad mein specific IPs pe lock kar denge
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
app.include_router(env_manager.router, prefix="/api", tags=["Environment Variables"])

# 3. User Dashboard Data (Naya Add Hua Hai 🚀)
app.include_router(services.router, prefix="/api", tags=["User Services Dashboard"])


# ==========================================
# 🚀 ROOT ENDPOINT (Health Check)
# ==========================================
@app.get("/", tags=["Root"])
async def root_check():
    """
    Ye check karne ke liye ki tera Cloud API server zinda hai ya nahi.
    """
    return {
        "status": "success",
        "message": "🚀 Welcome to My Custom Cloud Engine!",
        "engine_state": "Online & Running",
        "database": "MongoDB Connected",
        "tip": "Visit /docs to test the APIs."
    }
    
