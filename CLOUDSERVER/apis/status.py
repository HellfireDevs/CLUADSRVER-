from fastapi import APIRouter
import psutil
import os

router = APIRouter()

@router.get("/status")
async def get_system_status():
    """
    VPS ka Live RAM aur CPU usage batayega.
    """
    # CPU aur RAM ki details nikalna
    cpu_usage = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    return {
        "status": "online",
        "system_metrics": {
            "cpu_load_percent": cpu_usage,
            "ram_used_mb": round(ram.used / (1024 * 1024), 2),
            "ram_total_mb": round(ram.total / (1024 * 1024), 2),
            "ram_percent": ram.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2)
        },
        "message": "🔥 API Engine is running smoothly!"
    }
  
