from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging
import asyncio
import json
import time
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.redis_store import commit_timeline, redis_client

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



@app.websocket("/ws/meeting-stream")
async def meeting_stream(websocket: WebSocket):
    """
    Accepts a WebSocket connection for continuous bidirectional communication.
    In the real app, this will receive audio bytes from the Chrome extension.
    """
    await websocket.accept()
    logger.info("Client connected to meeting stream!")
    
    internal_queue = asyncio.Queue(maxsize=100)
    
    async def process_worker():
        while True:
            try:
                packet = await internal_queue.get() 
                try:
                    logger.info(f"Processed packet of size {len(packet)} bytes from queue")
                    simulated_text = f"Simulated STT for {len(packet)} bytes."
                    await commit_timeline("meeting_123", "User A", simulated_text)
                    
                except Exception as e:
                    logger.error(f"Failed processing individual frame context: {e}")
                finally:
                    internal_queue.task_done()
            except asyncio.CancelledError:
                break

    worker_task = asyncio.create_task(process_worker())
    
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
        
        worker_task.cancel()
        await asyncio.gather(worker_task, return_exceptions=True)
