from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

router = APIRouter()

# User API mein kya data bhejega, uska format
class EnvPayload(BaseModel):
    bot_folder_path: str   # Example: "/home/ubuntu/MYRDLMUSIC"
    env_data: dict         # Example: {"API_ID": "12345", "BOT_TOKEN": "xyz"}

# ==========================================
# ENV INJECTOR ENDPOINT
# ==========================================
@router.post("/inject-env")
async def inject_env_variables(payload: EnvPayload):
    """
    Ye endpoint external JSON se keys uthayega aur directly server pe .env file bana dega!
    """
    # Check karega ki wo folder VPS pe exist karta hai ya nahi
    if not os.path.exists(payload.bot_folder_path):
        raise HTTPException(status_code=404, detail="Bhai, wo bot ka folder hi nahi mila server pe!")

    env_file_path = os.path.join(payload.bot_folder_path, ".env")

    try:
        # Puraani .env ko overwrite karega fresh values ke sath
        with open(env_file_path, "w") as f:
            for key, value in payload.env_data.items():
                f.write(f"{key}={value}\n")
        
        return {
            "status": "success", 
            "message": f"🔥 .env file successfully injected into {payload.bot_folder_path}!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing .env file: {str(e)}")
      
