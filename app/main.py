from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Real-Time Meeting Copilot",
    description="Backend for processing real-time meeting transcripts.",
    version="0.1.0"
)

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
    
    # The Asynchronous Queue Broker (Buffer)
    internal_queue = asyncio.Queue(maxsize=100)
    
    # --- WORKER (The Consumer) ---
    async def process_worker():
        while True:
            try:
                packet = await internal_queue.get() 
                try:
                    logger.info(f"Processed packet of size {len(packet)} bytes from queue")
                except Exception as e:
                    logger.error(f"Failed processing individual frame context: {e}")
                finally:
                    internal_queue.task_done()
            except asyncio.CancelledError:
                break

    worker_task = asyncio.create_task(process_worker())
    
    # --- LISTENER (The Producer) ---
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
