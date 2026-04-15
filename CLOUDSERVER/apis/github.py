import os
import httpx  # 🚀 Naya Fast Async Library
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

# Apne Imports
from CLOUDSERVER.database.user import update_github_token, remove_github_token, get_user_by_username
from CLOUDSERVER.auth.verify import verify_api_key

router = APIRouter()

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

FRONTEND_REDIRECT_URL = "https://cluadwebsite.vercel.app/deploy"

# ==========================================
# 1. GITHUB LOGIN URL GENERATOR
# ==========================================
@router.get("/github/login")
async def github_login(username: str):
    url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo&state={username}"
    return {"status": "success", "url": url}

# ==========================================
# 2. GITHUB CALLBACK (Magic Happens Here)
# ==========================================
@router.get("/github/callback")
async def github_callback(code: str, state: str):
    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    payload = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code
    }
    
    # 🚀 Async HTTP Request
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, json=payload, headers=headers)
        resp_data = resp.json()
        access_token = resp_data.get("access_token")

        if access_token:
            # 🚀 Token se user ka GitHub Username nikalo bina server ko block kiye
            user_resp = await client.get(
                "https://api.github.com/user", 
                headers={"Authorization": f"Bearer {access_token}"}
            )
            gh_username = user_resp.json().get("login")

            # Database mein Token save kar do
            await update_github_token(username=state, token=access_token, github_username=gh_username)

    return RedirectResponse(url=FRONTEND_REDIRECT_URL)

# ==========================================
# 3. FETCH REPOS (Public + Private)
# ==========================================
@router.get("/github/repos")
async def get_github_repos(current_user: str = Depends(verify_api_key)):
    user = await get_user_by_username(current_user)
    token = user.get("github_token")
    gh_username = user.get("github_username")
    
    if not token:
        return {"status": "disconnected", "repos": []}

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    url = "https://api.github.com/user/repos?sort=pushed&per_page=100"
    
    # 🚀 Async Repo Fetch
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        await remove_github_token(current_user)
        return {"status": "disconnected", "repos": []}

    repos = resp.json()
    
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
    
