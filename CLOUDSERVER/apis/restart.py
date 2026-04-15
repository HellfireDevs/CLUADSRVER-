from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from CLOUDSERVER.core_utils.server_ops import restart_pm2

router = APIRouter()

# User se PM2 app ka naam lene ke liye format
class RestartPayload(BaseModel):
    pm2_app_name: str

@router.post("/restart")
async def manual_restart(payload: RestartPayload, background_tasks: BackgroundTasks):
    """
    Ek click mein PM2 process ko restart marne wala API.
    """
    try:
        # Background task mein restart bhej diya taaki API turant response de de
        background_tasks.add_task(restart_pm2, payload.pm2_app_name)
        
        return {
            "status": "success",
            "message": f"🔄 Restart signal sent successfully for '{payload.pm2_app_name}'. Bot should be back online in seconds!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restart API crash: {str(e)}")
      
