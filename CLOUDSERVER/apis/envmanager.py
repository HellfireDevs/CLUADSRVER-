from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os
import shutil
import subprocess

# Database & Security
from CLOUDSERVER.auth.verify import verify_api_key
from CLOUDSERVER.database.deploys import (
    get_bot_by_name, 
    update_bot_repo_details, 
    update_bot_env_vars, 
    delete_bot_from_db
)

router = APIRouter()

# ==========================================
# 📥 PAYLOAD MODELS
# ==========================================
class EditEnvPayload(BaseModel):
    app_name: str
    env_vars: dict  # Example: {"API_KEY": "123", "PORT": "8080"}

class EditRepoPayload(BaseModel):
    app_name: str
    new_repo_url: str
    new_repo_name: str
    new_start_cmd: str

class DeleteBotPayload(BaseModel):
    app_name: str

# ==========================================
# 1. ⚙️ EDIT / INJECT .ENV FILE
# ==========================================
@router.post("/edit-env")
async def edit_environment_variables(
    payload: EditEnvPayload,
    current_user: str = Depends(verify_api_key)
):
    """
    Website se JSON aayega aur ye VPS mein seedha .env file likh dega.
    """
    bot_info = await get_bot_by_name(payload.app_name)
    
    if not bot_info or bot_info["owner"] != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized or Bot not found!")

    folder_path = bot_info["folder_path"]
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)

    env_file_path = os.path.join(folder_path, ".env")
    
    try:
        # VPS par .env file banakar usme data likh rahe hain
        with open(env_file_path, "w") as env_file:
            for key, value in payload.env_vars.items():
                env_file.write(f"{key}={value}\n")
        
        # MongoDB mein backup ke liye save kar do
        await update_bot_env_vars(payload.app_name, payload.env_vars)

        return {
            "status": "success", 
            "message": f"✅ .env variables successfully saved for {payload.app_name}. Please restart the bot to apply changes."
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .env file: {str(e)}")

# ==========================================
# 2. 🔄 CHANGE REPOSITORY DETAILS
# ==========================================
@router.post("/edit-repo")
async def edit_bot_repository(
    payload: EditRepoPayload,
    current_user: str = Depends(verify_api_key)
):
    """
    Agar user ne galat repo daal di thi, ya start command change karni hai.
    """
    bot_info = await get_bot_by_name(payload.app_name)
    
    if not bot_info or bot_info["owner"] != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized or Bot not found!")

    # MongoDB update
    updated = await update_bot_repo_details(
        payload.app_name, 
        payload.new_repo_url, 
        payload.new_repo_name, 
        payload.new_start_cmd
    )
    
    if not updated:
        raise HTTPException(status_code=500, detail="Database update failed.")

    return {
        "status": "success", 
        "message": f"✅ Repo details updated for {payload.app_name}. Please hit Reset to clone new repo."
    }

# ==========================================
# 3. 🗑️ DELETE APP / BOT COMPLETELY
# ==========================================
@router.post("/delete-bot")
async def delete_bot_completely(
    payload: DeleteBotPayload,
    current_user: str = Depends(verify_api_key)
):
    """
    Ye bot ko PM2 se hatayega, folder delete karega aur DB se bhi uda dega.
    """
    bot_info = await get_bot_by_name(payload.app_name)
    
    if not bot_info or bot_info["owner"] != current_user:
        raise HTTPException(status_code=403, detail="Unauthorized or Bot not found!")

    app_name = payload.app_name
    folder_path = bot_info["folder_path"]

    try:
        # 1. PM2 aur Docker se Delete karo (Agar running hai toh hat jayega)
        subprocess.run(["pm2", "delete", app_name], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        subprocess.run(["docker", "rm", "-f", app_name.lower()], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

        # 2. VPS se poora folder delete karo (Space free karne ke liye)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path, ignore_errors=True)
            print(f"🗑️ [CLEANUP] Folder deleted: {folder_path}")

        # 3. MongoDB se record delete karo
        db_deleted = await delete_bot_from_db(app_name)
        
        if not db_deleted:
            print("⚠️ Database se delete nahi hua shayad pehle hi delete ho gaya tha.")

        return {
            "status": "success", 
            "message": f"✅ Bot '{app_name}' has been permanently deleted from server and database."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete bot: {str(e)}")
        
