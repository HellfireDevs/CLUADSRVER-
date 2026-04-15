from fastapi import APIRouter
import time

router = APIRouter()

# API kab start hua tha (Uptime calculate karne ke liye)
SERVER_START_TIME = time.time()

@router.get("/ping")
async def server_ping():
    """
    API ka response time aur uptime check karne ke liye.
    """
    uptime_seconds = int(time.time() - SERVER_START_TIME)
    
    # Seconds ko proper format mein convert karna
    minutes, seconds = divmod(uptime_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    return {
        "status": "pong 🏓",
        "ping": "Server is completely responsive.",
        "uptime": uptime_str
    }
  
