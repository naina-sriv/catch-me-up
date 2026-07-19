from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging
import asyncio
import json
import time
import os
import websockets as ws_client
from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app.redis_store import commit_timeline, redis_client
from app.vector_store import evict_old_transcripts
from app.agent import ask_copilot
from app.auth import create_access_token, verify_token, require_role, TokenData
from fastapi import Depends, Query


load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Real-Time Meeting Copilot",
    description="Backend for processing real-time meeting transcripts.",
    version="0.1.0"
)

templates = Jinja2Templates(directory="app/templates")

@app.get("/summary/{meeting_id}", response_class=HTMLResponse, tags=["Dashboard"])
async def view_universal_mom_dashboard(request: Request, meeting_id: str):
    """
    Decoupled Universal Dashboard (Chunk 3)
    Reads directly from Redis ZSET to display the live timeline in < 1ms.
    """
    
    zset_key = f"meeting:{meeting_id}:timeline"
    raw_data = await redis_client.zrange(zset_key, 0, -1, withscores=True)
    
    compiled_lines = []
    for row, score in raw_data:
        try:
            data = json.loads(row)
            compiled_lines.append({
                "time": time.strftime('%H:%M:%S', time.gmtime(score)),
                "speaker": data.get("speaker", "Unknown"),
                "text": data.get("text", "")
            })
        except:
            pass
            
    return templates.TemplateResponse("mom.html", {
        "request": request, 
        "meeting_id": meeting_id, 
        "timeline": compiled_lines
    })



@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "message": "Server is up and running!"}

# ==========================================
# 🔐 AUTHENTICATION ROUTE (Chunk 6)
# ==========================================
class TokenRequest(BaseModel):
    username: str
    roles: list[str]

@app.post("/auth/manual-token", tags=["Security"])
async def generate_manual_token(request: TokenRequest):
    """
    Manually creates a cryptographically signed JWT for local testing.
    In production, this would be handled via Discord OAuth2 Login!
    """
    token = create_access_token({"username": request.username, "roles": request.roles})
    return {"access_token": token, "token_type": "bearer"}

# ==========================================
# 🧹 EVICTION CASCADE ROUTE (Chunk 4)
# ==========================================
@app.post("/meetings/{meeting_id}/evict", tags=["Vector Store"])
async def trigger_eviction(meeting_id: str, max_age_seconds: float = 30.0):
    """
    Manually triggers the Eviction Cascade.
    In a real production environment, this would run automatically in the background (Cron Job).
    """
    logger.info(f"Triggering eviction cascade for meeting {meeting_id} (max_age={max_age_seconds}s)")
    evicted_count = await evict_old_transcripts(meeting_id, max_age_seconds)
    
    return {
        "status": "success", 
        "message": f"Evicted {evicted_count} transcripts to Qdrant and deleted them from Redis."
    }

# ==========================================
# 🤖 COPILOT AGENT ROUTE (Chunk 5)
# ==========================================
class QuestionRequest(BaseModel):
    question: str

@app.post("/meetings/{meeting_id}/ask", tags=["Agent"])
async def ask_meeting_copilot(
    meeting_id: str, 
    request: QuestionRequest,
    # Injecting the Security dependency!
    user: TokenData = Depends(require_role("listener"))
):
    """
    Asks the LangChain Copilot a question about the meeting.
    Requires the 'listener' role to access!
    The Agent retrieves context from Qdrant and returns an AI-generated answer.
    """
    logger.info(f"Copilot asked: '{request.question}' for meeting {meeting_id}")
    answer = await ask_copilot(meeting_id, request.question)
    
    return {
        "status": "success",
        "question": request.question,
        "answer": answer
    }



@app.websocket("/ws/meeting-stream")
async def meeting_stream(websocket: WebSocket, token: str = Query(...)):
    """
    Accepts a WebSocket connection for continuous bidirectional communication.
    Secured via JWT query parameter.
    """
    await websocket.accept()
    
    # Authenticate the WebSocket connection instantly!
    try:
        user_data = verify_token(token)
        if "speaker" not in user_data.roles:
            await websocket.send_text("Error: You lack the 'speaker' role!")
            await websocket.close(code=1008)
            return
    except Exception as e:
        await websocket.close(code=1008)
        return
        
    logger.info(f"User {user_data.username} successfully connected to meeting stream!")
    
    internal_queue = asyncio.Queue(maxsize=100)
    
    try:
        dg_socket = await ws_client.connect(
            "wss://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
            extra_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}
        )
        logger.info("Connected to Deepgram Live API")
    except Exception as e:
        logger.error(f"Failed to connect to Deepgram: {e}")
        await websocket.close(code=1011)
        return
    
    async def process_worker():
        while True:
            try:
                packet = await internal_queue.get() 
                try:
                    await dg_socket.send(packet)
                except Exception as e:
                    logger.error(f"Failed to send to Deepgram: {e}")
                finally:
                    internal_queue.task_done()
            except asyncio.CancelledError:
                break
                
    async def deepgram_receiver():
        try:
            async for message in dg_socket:
                data = json.loads(message)
                if data.get("type") == "Results":
                    transcript = data["channel"]["alternatives"][0]["transcript"]
                    if transcript and transcript.strip():
                        logger.info(f"Deepgram Transcribed: {transcript}")
                        await commit_timeline("meeting_123", user_data.username, transcript)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Deepgram receiver error: {e}")

    worker_task = asyncio.create_task(process_worker())
    receiver_task = asyncio.create_task(deepgram_receiver())
    
    try:
        while True:
            data = await websocket.receive_bytes()
            await internal_queue.put(data)
            
    except WebSocketDisconnect:
        logger.info("Client disconnected from the meeting stream.")
    finally:
        try:
            await asyncio.wait_for(internal_queue.join(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Queue draining timed out. Forcing eviction cascade.")
        try:
            await dg_socket.send(b'') 
            await dg_socket.close()
        except:
            pass
            
        worker_task.cancel()
        receiver_task.cancel()
        await asyncio.gather(worker_task, receiver_task, return_exceptions=True)
