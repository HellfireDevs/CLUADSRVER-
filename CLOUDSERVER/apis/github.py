import os
import uuid
import httpx  # 🚀 Fast Async Library
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

# Apne Imports
from CLOUDSERVER.database.user import update_github_token, remove_github_token, get_user_by_username
from CLOUDSERVER.auth.verify import verify_api_key
from CLOUDSERVER.database.database import users_collection # 🔥 Login save karne ke liye

router = APIRouter()

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# Redirect URLs
FRONTEND_DEPLOY_URL = "https://cluadwebsite.vercel.app/deploy"
FRONTEND_LOGIN_URL = os.getenv("FRONTEND_URL", "https://cluadwebsite.vercel.app")

# ==========================================
# 1. GITHUB LOGIN URL GENERATOR
# ==========================================
@router.get("/github/login")
async def github_login(username: str):
    # 🔥 NAYA: scope mein 'user:email' add kiya taaki login ke time email nikal sakein
    url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo%20user:email&state={username}"
    return {"status": "success", "url": url}

# ==========================================
# 2. GITHUB CALLBACK (Magic Multiplexer) 🪄
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
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, json=payload, headers=headers)
        resp_data = resp.json()
        access_token = resp_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub Auth Failed!")

        # User ka basic data nikalo
        user_resp = await client.get("https://api.github.com/user", headers={"Authorization": f"Bearer {access_token}"})
        gh_username = user_resp.json().get("login")

        # ========================================================
        # 🟢 SCENARIO A: SAAS ACCOUNT LOGIN / SIGNUP FLOW
        # ========================================================
        if state == "AUTH_LOGIN_FLOW":
            # GitHub se primary email nikalo (kyunki profile me kabhi kabhi hidden hoti hai)
            email_resp = await client.get("https://api.github.com/user/emails", headers={"Authorization": f"Bearer {access_token}"})
            emails = email_resp.json()
            
            # Find primary email
            primary_email = None
            if isinstance(emails, list):
                for e in emails:
                    if e.get("primary"):
                        primary_email = e.get("email")
                        break
            
            if not primary_email:
                primary_email = f"{gh_username}@github.dummy.com" # Fallback

            # Check karo user pehle se DB me hai ya nahi
            user = await users_collection.find_one({"email": primary_email})
            
            if not user:
                # Naya account bana do!
                api_key = f"nex_{uuid.uuid4().hex}"
                new_user = {
                    "username": gh_username,
                    "email": primary_email,
                    "password": "", 
                    "api_key": api_key,
                    "is_premium": False,
                    "github_token": access_token, # Ek teer se do nishane (Login + Repo link done)
                    "github_username": gh_username,
                    "created_at": datetime.utcnow()
                }
                await users_collection.insert_one(new_user)
                final_username = gh_username
            else:
                # Purana user hai
                api_key = user.get("api_key")
                final_username = user.get("username")
                # Token update kar do
                await update_github_token(username=final_username, token=access_token, github_username=gh_username)

            # Redirect back to frontend login page with API Key
            return RedirectResponse(url=f"{FRONTEND_LOGIN_URL}/login?api_key={api_key}&username={final_username}")


        # ========================================================
        # 🔵 SCENARIO B: DEPLOY PAGE REPO LINKING FLOW
        # ========================================================
        else:
            # Agar state me "AUTH_LOGIN_FLOW" nahi hai, matlab user ne Deploy page se click kiya tha (state = uski asli username)
            await update_github_token(username=state, token=access_token, github_username=gh_username)
            return RedirectResponse(url=FRONTEND_DEPLOY_URL)


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
    
