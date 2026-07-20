from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
from typing import Optional
import logging
import asyncio
import json
import time
import os
import websockets as ws_client
from dotenv import load_dotenv

from app.redis_store import (
    commit_timeline, get_timeline, get_meeting_visibility,
    set_public_toggle, heartbeat_node, get_active_nodes, get_server_sessions,
    redis_client
)
from app.vector_store import evict_old_transcripts
from app.agent import ask_copilot
from app.auth import create_access_token, verify_token, require_scope, require_role, TokenData

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Catch-Me-Up API",
    description="Real-time meeting transcription and AI catch-up backend.",
    version="2.0.0"
)

templates = Jinja2Templates(directory="app/templates")


# ============================================================
# 🏥 HEALTH
# ============================================================
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


# ============================================================
# 🔐 AUTH — Manual token for testing & generic mode
# ============================================================
class TokenRequest(BaseModel):
    username: str
    role: str = "member"         # "admin" | "member"
    meeting_id: str = "meeting_123"

@app.post("/auth/manual-token", tags=["Auth"])
async def generate_manual_token(request: TokenRequest):
    """
    Issues a signed JWT for local testing or Generic Mode.
    In Discord-native mode this is replaced by the Discord Bot flow.
    """
    token = create_access_token({
        "username": request.username,
        "role": request.role,
        "meeting_id": request.meeting_id,
        "joined_at": time.time(),
        "scope": "ingest:stream read:transcript",
    })
    return {"access_token": token, "token_type": "bearer"}


# ============================================================
# 📺 DASHBOARD — Role-scoped transcript view
# ============================================================
@app.get("/summary/{meeting_id}", response_class=HTMLResponse, tags=["Dashboard"])
async def view_transcript_dashboard(
    request: Request,
    meeting_id: str,
    token: Optional[str] = Query(None)
):
    """
    Renders the meeting transcript dashboard.
    - Admins see the full :admin ZSET (all content from T=0)
    - Members see only :public ZSET from max(joined_at, public_opened_at)
    """
    role = "member"
    joined_at = 0.0
    username = "Anonymous"

    if token:
        try:
            user = verify_token(token)
            role = user.role
            joined_at = user.joined_at
            username = user.username
        except Exception:
            pass  # Unauthenticated gets member-level public view

    timeline = await get_timeline(meeting_id, role, joined_at)

    return templates.TemplateResponse(
        request=request,
        name="mom.html",
        context={
            "meeting_id": meeting_id,
            "timeline": timeline,
            "role": role,
            "username": username,
        }
    )


# ============================================================
# 🏢 COMMUNITY DASHBOARD — All sessions for a server
# ============================================================
@app.get("/dashboard/{server_id}", tags=["Dashboard"])
async def server_dashboard(
    server_id: str,
    user: TokenData = Depends(require_scope("read:transcript"))
):
    """
    Returns all past meeting sessions for a Discord server.
    Admins see all sessions; members only see sessions with public content.
    """
    sessions = await get_server_sessions(server_id, user.role)
    return {"server_id": server_id, "role": user.role, "sessions": sessions}


# ============================================================
# 🔘 MEETING CONTROLS — Admin only
# ============================================================
class ToggleRequest(BaseModel):
    is_public: bool

@app.patch("/meetings/{meeting_id}/toggle-public", tags=["Meeting Controls"])
async def toggle_public_transcript(
    meeting_id: str,
    body: ToggleRequest,
    user: TokenData = Depends(require_role("admin"))
):
    """
    Admin-only: toggles whether new transcript chunks are written to the public ZSET.
    Once opened (is_public=True), public_opened_at is recorded permanently.
    """
    await set_public_toggle(meeting_id, body.is_public)
    status = "PUBLIC" if body.is_public else "ADMIN-ONLY"
    logger.info(f"[{meeting_id}] Meeting visibility set to {status} by {user.username}")
    return {"meeting_id": meeting_id, "public_transcript": body.is_public}


@app.get("/meetings/{meeting_id}/nodes", tags=["Meeting Controls"])
async def get_ingestion_nodes(
    meeting_id: str,
    user: TokenData = Depends(require_scope("ingest:stream"))
):
    """
    Returns list of currently active ingestion node user_ids.
    Lets any speaker check if the meeting is covered before stepping away.
    """
    nodes = await get_active_nodes(meeting_id)
    return {
        "meeting_id": meeting_id,
        "active_node_count": len(nodes),
        "nodes": nodes
    }


# ============================================================
# 🧹 EVICTION CASCADE
# ============================================================
@app.post("/meetings/{meeting_id}/evict", tags=["Vector Store"])
async def trigger_eviction(
    meeting_id: str,
    max_age_seconds: float = 30.0,
    user: TokenData = Depends(require_role("admin"))
):
    """Admin-only: manually triggers eviction of old Redis chunks to Qdrant."""
    evicted = await evict_old_transcripts(meeting_id, max_age_seconds)
    return {"status": "success", "evicted_count": evicted}


# ============================================================
# 🤖 COPILOT AGENT — Visibility-scoped RAG
# ============================================================
class QuestionRequest(BaseModel):
    question: str

@app.post("/meetings/{meeting_id}/ask", tags=["Agent"])
async def ask_meeting_copilot(
    meeting_id: str,
    request: QuestionRequest,
    user: TokenData = Depends(require_scope("read:transcript"))
):
    """
    Asks the Catch-Me-Up Copilot a question about the meeting.
    The RAG pipeline is scoped to the user's role:
    - Admin: searches all vectors including admin-only content
    - Member: searches ONLY public vectors — admin content is never leaked
    """
    logger.info(f"[{user.role}] {user.username} asked: '{request.question}' for {meeting_id}")
    answer = await ask_copilot(meeting_id, request.question, role=user.role)
    return {
        "question": request.question,
        "answer": answer,
        "scoped_to": user.role
    }


# ============================================================
# 🎙️ WEBSOCKET — Audio ingestion (open to all valid JWT holders)
# ============================================================
@app.websocket("/ws/meeting-stream")
async def meeting_stream(websocket: WebSocket, token: str = Query(...)):
    """
    Audio ingestion WebSocket.
    ANY valid JWT holder can stream audio (ingest is not role-restricted).
    Role only affects read access, not ingestion.

    Transcript chunks are written to:
      - :admin ZSET always
      - :public ZSET only if the public toggle is ON
    """
    await websocket.accept()

    try:
        user_data = verify_token(token)
        if "ingest:stream" not in user_data.scope:
            await websocket.send_text("Error: Missing ingest:stream scope")
            await websocket.close(code=1008)
            return
    except Exception:
        await websocket.close(code=1008)
        return

    meeting_id = user_data.meeting_id or "meeting_123"
    logger.info(f"[{user_data.role}] {user_data.username} connected to {meeting_id}")

    # Register as active node
    await heartbeat_node(meeting_id, user_data.username)

    # Init meeting config if first node
    config_key = f"meeting:{meeting_id}:config"
    if not await redis_client.exists(config_key):
        await redis_client.hset(config_key, mapping={
            "started_at": str(time.time()),
            "public_transcript": "false",
        })

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
                    # Refresh heartbeat on every audio chunk
                    await heartbeat_node(meeting_id, user_data.username)
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
                        logger.info(f"Transcribed: {transcript}")
                        # Determine visibility from current meeting toggle
                        visibility = await get_meeting_visibility(meeting_id)
                        await commit_timeline(
                            meeting_id,
                            user_data.username,
                            transcript,
                            visibility=visibility
                        )
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
        logger.info(f"{user_data.username} disconnected from {meeting_id}")
    finally:
        try:
            await asyncio.wait_for(internal_queue.join(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Queue drain timed out.")
        try:
            await dg_socket.send(b'')
            await dg_socket.close()
        except Exception:
            pass
        worker_task.cancel()
        receiver_task.cancel()
        await asyncio.gather(worker_task, receiver_task, return_exceptions=True)
