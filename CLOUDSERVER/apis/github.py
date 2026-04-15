import os
import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

# Apne Imports
from CLOUDSERVER.database.user import update_github_token, remove_github_token, get_user_by_username
from CLOUDSERVER.auth.verify import verify_api_key

router = APIRouter()

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# 🚨 DHYAN RAKHNA: Agar locally test kar raha hai toh isko http://localhost:5173/deploy kar dena
FRONTEND_REDIRECT_URL = "https://cluadwebsite.vercel.app/deploy"

# ==========================================
# 1. GITHUB LOGIN URL GENERATOR
# ==========================================
@router.get("/github/login")
async def github_login(username: str):
    """Frontend isko call karega GitHub ka redirect URL lene ke liye"""
    # 'scope=repo' dena zaroori hai private repos access karne ke liye
    url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo&state={username}"
    return {"status": "success", "url": url}

# ==========================================
# 2. GITHUB CALLBACK (Magic Happens Here)
# ==========================================
@router.get("/github/callback")
async def github_callback(code: str, state: str):
    """GitHub authorization ke baad is route pe code wapas bhejega"""
    # 1. Code ke badle Access Token maango
    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    payload = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code
    }
    
    resp = requests.post(token_url, json=payload, headers=headers).json()
    access_token = resp.get("access_token")

    if access_token:
        # 2. Token se user ka GitHub Username nikalo
        user_resp = requests.get("https://api.github.com/user", headers={"Authorization": f"Bearer {access_token}"}).json()
        gh_username = user_resp.get("login")

        # 3. Database mein Token save kar do (state mein humne apna 'username' bheja tha)
        await update_github_token(username=state, token=access_token, github_username=gh_username)

    # 4. User ko wapas Frontend Deploy page pe bhej do
    return RedirectResponse(url=FRONTEND_REDIRECT_URL)

# ==========================================
# 3. FETCH REPOS (Public + Private)
# ==========================================
@router.get("/github/repos")
async def get_github_repos(current_user: str = Depends(verify_api_key)):
    """User ke saare latest repos fetch karega"""
    user = await get_user_by_username(current_user)
    token = user.get("github_token")
    gh_username = user.get("github_username")
    
    if not token:
        return {"status": "disconnected", "repos": []}

    # GitHub se repos maango (Sort by letest push, Max 100 limit)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    url = "https://api.github.com/user/repos?sort=pushed&per_page=100"
    
    resp = requests.get(url, headers=headers)

    if resp.status_code != 200:
        # Agar token expire ho gaya ho toh disconnect kar do
        await remove_github_token(current_user)
        return {"status": "disconnected", "repos": []}

    repos = resp.json()
    
    # Filter karke sirf kaam ka data frontend ko bhejenge
    clean_repos = []
    for repo in repos:
        clean_repos.append({
            "id": repo["id"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "private": repo["private"],
            "url": repo["clone_url"],
            "updated_at": repo["pushed_at"]
        })

    return {
        "status": "connected", 
        "github_username": gh_username, 
        "repos": clean_repos
    }

# ==========================================
# 4. DISCONNECT GITHUB
# ==========================================
@router.post("/github/disconnect")
async def disconnect_github(current_user: str = Depends(verify_api_key)):
    await remove_github_token(current_user)
    return {"status": "success", "message": "GitHub disconnected successfully!"}
  
