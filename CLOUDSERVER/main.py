from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Baad mein jab hum apis folder mein files banayenge, tab inko uncomment karenge
# from CLOUDSERVER.apis import deploy, restart, status

app = FastAPI(
    title="My Custom Cloud API ☁️",
    description="Render aur Heroku se bhi fast custom deployment API 🔥",
    version="1.0.0",
    docs_url="/docs",    # Yahan se tu bina website ke API test karega
    redoc_url="/redoc"
)

# CORS Setup: Taaki future mein kisi bhi website ya dashboard se ye API connect ho sake
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Abhi sabko allow kiya hai, baad mein strictly apne IP pe lock kar denge
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# API ROUTERS (Linking other folders)
# ==========================================
# Jaise-jaise hum apis/ folder mein files banayenge, unko yahan link karte jayenge
# app.include_router(deploy.router, prefix="/api", tags=["Deployment"])
# app.include_router(restart.router, prefix="/api", tags=["Process Management"])
# app.include_router(status.router, prefix="/api", tags=["System Status"])


# ==========================================
# ROOT ENDPOINT (Health Check)
# ==========================================
@app.get("/", tags=["Health Check"])
async def root_check():
    """
    Ye check karne ke liye ki tera Cloud API server zinda hai ya nahi.
    """
    return {
        "status": "success",
        "message": "🚀 Welcome to My Cloud API Engine!",
        "engine_state": "Online & Running",
        "tip": "Visit /docs to test the APIs."
    }

