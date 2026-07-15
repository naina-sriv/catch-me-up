import json
import time
from redis import asyncio as aioredis
import logging

logger = logging.getLogger(__name__)

redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)

async def commit_timeline(meeting_id: str, speaker: str, text: str):
    """
    Saves a transcript to a Redis Sorted Set (ZSET) using the Unix timestamp as the score.
    """
    zset_key = f"meeting:{meeting_id}:timeline"
    payload = json.dumps({"speaker": speaker, "text": text.strip()})
    
    try:
        await redis_client.zadd(zset_key, {payload: time.time()})
        await redis_client.expire(zset_key, 3600)
        
        logger.info(f"Committed to timeline {zset_key}: {text.strip()[:20]}...")
    except Exception as e:
        logger.error(f"Failed to commit timeline to Redis: {e}")
