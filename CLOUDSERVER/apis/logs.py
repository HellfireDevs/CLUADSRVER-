from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio

router = APIRouter()

# ==========================================
# 📡 LIVE LOGS STREAMING (WebSockets)
# ==========================================
@router.websocket("/stream/{app_name}")
async def stream_logs(websocket: WebSocket, app_name: str, use_docker: bool = False):
    await websocket.accept()
    print(f"🔗 [WEBSOCKET] Client connected for logs: {app_name} (Docker: {use_docker})")
    
    process = None
    try:
        if use_docker:
            # 🐳 Docker ke naam mein space nahi ho sakta, isliye hata diya
            safe_docker_name = app_name.lower().replace(" ", "")
            cmd = ["docker", "logs", "-f", "--tail", "50", safe_docker_name]
        else:
            # 🔥 PM2 command
            cmd = ["pm2", "logs", app_name, "--raw", "--lines", "50"]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT 
        )

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            await websocket.send_text(line.decode('utf-8').strip())

    except WebSocketDisconnect:
        print(f"🔌 [WEBSOCKET] Client disconnected from {app_name}. Stopping stream...")
        
    except Exception as e:
        print(f"❌ [LOGS ERROR] {str(e)}")
        try:
            await websocket.send_text(f"❌ System Error: {str(e)}")
        except:
            pass 
            
    finally:
        if process and process.returncode is None:
            process.terminate()
            print(f"🧹 [CLEANUP] Killed log process for {app_name}")
            
