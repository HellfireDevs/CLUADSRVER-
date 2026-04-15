from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio

router = APIRouter()

# ==========================================
# 📡 LIVE LOGS STREAMING (WebSockets)
# ==========================================
@router.websocket("/stream/{app_name}")
async def stream_logs(websocket: WebSocket, app_name: str, use_docker: bool = False):
    """
    Ye endpoint ek Live Pipe banayega. 
    Frontend/Terminal isse connect karega aur live errors dekhega.
    """
    # 1. Connection Accept karo
    await websocket.accept()
    print(f"🔗 [WEBSOCKET] Client connected for logs: {app_name} (Docker: {use_docker})")
    
    process = None
    try:
        # 2. Command decide karo (Docker vs PM2)
        if use_docker:
            # -f ka matlab 'follow' (live stream)
            cmd = ["docker", "logs", "-f", "--tail", "50", app_name]
        else:
            # pm2 logs live output deta hai
            cmd = ["pm2", "logs", app_name, "--raw", "--lines", "50"]

        # 3. Asynchronous process start karo (VPS block nahi hoga)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT # Errors ko bhi standard output mein mix kar do
        )

        # 4. Infinite loop jo pipe se data nikal kar client ko bhejega
        while True:
            line = await process.stdout.readline()
            
            # Agar process ruk gaya toh loop tod do
            if not line:
                break
                
            # Line ko text mein convert karke bhej do
            await websocket.send_text(line.decode('utf-8').strip())

    except WebSocketDisconnect:
        # 🚨 MAIN LOGIC: Jaise hi user page katega, ye trigger hoga!
        print(f"🔌 [WEBSOCKET] Client disconnected from {app_name}. Stopping log stream...")
        
    except Exception as e:
        print(f"❌ [LOGS ERROR] {str(e)}")
        try:
            await websocket.send_text(f"❌ Error: {str(e)}\n⚠️ Please refresh the page or reconnect.")
        except:
            pass # Agar bhejne mein error aaye toh ignore karo
            
    finally:
        # 🧹 CLEANUP: Background task ko kill karo taaki RAM free ho jaye
        if process and process.returncode is None:
            process.terminate()
            print(f"🧹 [CLEANUP] Killed log process for {app_name}")
          
