import json
import time
import logging
from redis import asyncio as aioredis
import os

logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = aioredis.from_url(redis_url, decode_responses=True)


async def commit_timeline(meeting_id: str, speaker: str, text: str, visibility: str = "public"):
    """
    Saves a transcript chunk to the appropriate Redis ZSETs based on visibility.

    Dual ZSET model:
      - meeting:{id}:timeline:admin  → ALL chunks (admin-only + public)
      - meeting:{id}:timeline:public → ONLY public chunks

    This means admins always query :admin and get everything.
    Members query :public and only get what the admin has opened up.
    """
    timestamp = time.time()
    payload = json.dumps({
        "speaker": speaker,
        "text": text.strip(),
        "visibility": visibility,
        "ts": timestamp
    })

    try:
        # Always write to the admin ZSET
        admin_key = f"meeting:{meeting_id}:timeline:admin"
        await redis_client.zadd(admin_key, {payload: timestamp})
        await redis_client.expire(admin_key, 7200)

        # Only write to public ZSET when visibility is "public"
        if visibility == "public":
            public_key = f"meeting:{meeting_id}:timeline:public"
            await redis_client.zadd(public_key, {payload: timestamp})
            await redis_client.expire(public_key, 7200)

        logger.info(f"[{visibility.upper()}] Committed to {meeting_id}: {text.strip()[:40]}...")
    except Exception as e:
        logger.error(f"Failed to commit timeline to Redis: {e}")


async def get_timeline(meeting_id: str, role: str, joined_at: float = 0.0) -> list:
    """
    Retrieves the transcript for a meeting, scoped by role and join time.

    - admin role: queries :admin ZSET from score=0 (full history)
    - member role: queries :public ZSET from max(joined_at, public_opened_at)
    """
    if role == "admin":
        key = f"meeting:{meeting_id}:timeline:admin"
        start_time = 0
    else:
        key = f"meeting:{meeting_id}:timeline:public"
        config_key = f"meeting:{meeting_id}:config"
        public_opened_at = await redis_client.hget(config_key, "public_opened_at")
        public_opened_at = float(public_opened_at) if public_opened_at else 0.0
        start_time = max(joined_at, public_opened_at)

    raw_data = await redis_client.zrangebyscore(key, start_time, "+inf", withscores=True)

    results = []
    for row, score in raw_data:
        try:
            data = json.loads(row)
            results.append({
                "time": time.strftime('%H:%M:%S', time.gmtime(score)),
                "speaker": data.get("speaker", "Unknown"),
                "text": data.get("text", ""),
                "visibility": data.get("visibility", "public")
            })
        except Exception:
            pass
    return results


async def get_meeting_visibility(meeting_id: str) -> str:
    """Returns 'public' or 'admin_only' based on current meeting config toggle."""
    config_key = f"meeting:{meeting_id}:config"
    val = await redis_client.hget(config_key, "public_transcript")
    return "public" if val == "true" else "admin_only"


async def set_public_toggle(meeting_id: str, is_public: bool):
    """Admin toggles whether new transcripts go to the public ZSET."""
    config_key = f"meeting:{meeting_id}:config"
    await redis_client.hset(config_key, "public_transcript", "true" if is_public else "false")
    if is_public:
        # Record the exact moment the meeting was opened to the public
        existing = await redis_client.hget(config_key, "public_opened_at")
        if not existing:
            await redis_client.hset(config_key, "public_opened_at", str(time.time()))


async def heartbeat_node(meeting_id: str, user_id: str):
    """Registers/refreshes an active ingestion node in Redis with a 20s TTL."""
    key = f"meeting:{meeting_id}:active_nodes"
    await redis_client.hset(key, user_id, str(time.time()))
    await redis_client.expire(key, 20)


async def get_active_nodes(meeting_id: str) -> list:
    """Returns a list of active ingestion node user_ids (those with recent heartbeats)."""
    key = f"meeting:{meeting_id}:active_nodes"
    cutoff = time.time() - 20
    all_nodes = await redis_client.hgetall(key)
    return [uid for uid, ts in all_nodes.items() if float(ts) > cutoff]


async def get_server_sessions(server_id: str, role: str) -> list:
    """
    Returns all past meeting sessions for a Discord server.
    Admins see all sessions. Members only see sessions with public content.
    """
    pattern = f"meeting:{server_id}:*:timeline:admin"
    keys = await redis_client.keys(pattern)
    sessions = []
    for key in keys:
        # Extract meeting_id from key pattern
        parts = key.split(":")
        if len(parts) >= 3:
            meeting_id = ":".join(parts[1:-2])
            config_key = f"meeting:{meeting_id}:config"
            started_at = await redis_client.hget(config_key, "started_at")
            has_public = await redis_client.exists(f"meeting:{meeting_id}:timeline:public")

            if role == "member" and not has_public:
                continue  # Members skip sessions with no public content

            sessions.append({
                "meeting_id": meeting_id,
                "started_at": float(started_at) if started_at else 0,
                "has_public_content": bool(has_public)
            })
    return sorted(sessions, key=lambda s: s["started_at"], reverse=True)
