from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import os

router = APIRouter()

# ==========================================
# 📡 1. LIVE RUNTIME LOGS (Jo tune banaya tha)
# ==========================================
@router.websocket("/stream/{app_name}")
async def stream_logs(websocket: WebSocket, app_name: str, use_docker: bool = False):
    await websocket.accept()
    print(f"🔗 [WEBSOCKET] Client connected for RUNTIME logs: {app_name} (Docker: {use_docker})")
    
    process = None
    try:
        if use_docker:
            # 🐳 Docker ke naam mein space nahi ho sakta
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

# ==========================================
# 🏗️ 2. LIVE BUILD LOGS (Render Style!)
# ==========================================
@router.websocket("/build-stream/{username}/{app_name}")
async def stream_build_logs(websocket: WebSocket, username: str, app_name: str):
    await websocket.accept()
    print(f"🔗 [WEBSOCKET] Client connected for BUILD logs: {app_name}")

    # Is path pe hum build ka data save karenge
    log_file_path = f"/home/ubuntu/nex_cloud_apps/{username}/{app_name}/build.log"
    process = None

    try:
        # Agar file abhi tak nahi bani (clone shuru nahi hua), toh wait karo
        while not os.path.exists(log_file_path):
            await websocket.send_text("⏳ Preparing deployment environment...")
            await asyncio.sleep(2)

        await websocket.send_text("🚀 Build process started! Streaming logs...\n")

        # Linux ka 'tail -f' command file ko live read karta hai
        process = await asyncio.create_subprocess_exec(
            "tail", "-f", "-n", "100", log_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT 
        )

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            text_line = line.decode('utf-8').strip()
            await websocket.send_text(text_line)
            
            # 🛑 SMART STOP: Agar build khatam ya fail ho gayi toh stream band kar do
            if "NEX_CLOUD_BUILD_COMPLETE" in text_line or "NEX_CLOUD_BUILD_FAILED" in text_line:
                await websocket.send_text("\n✅ Build stream disconnected.")
                break

    except WebSocketDisconnect:
        print(f"🔌 [WEBSOCKET] Client disconnected from build logs of {app_name}.")
        
    except Exception as e:
        print(f"❌ [BUILD LOGS ERROR] {str(e)}")
        
    finally:
        if process and process.returncode is None:
            process.terminate()
            
