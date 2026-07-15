import json
import logging
import uuid
import os
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.redis_store import redis_client

logger = logging.getLogger(__name__)


# We use a single synchronous memory client to avoid locking issues across LangChain and FastAPI!
qdrant_client = QdrantClient(location=":memory:")
COLLECTION_NAME = "meeting_transcripts"

def setup_qdrant_collection():
    """
    Ensures that our Qdrant collection exists before we try to save data to it.
    """
    if not qdrant_client.collection_exists(COLLECTION_NAME):
        # We define a 384-dimensional space (the size of HuggingFace MiniLM embeddings)
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")

def get_real_embedding(text: str) -> List[float]:
    """
    Uses a free, local HuggingFace model to generate embeddings directly on your CPU!
    This bypasses API key errors entirely.
    """
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return embeddings.embed_query(text)

async def evict_old_transcripts(meeting_id: str, max_age_seconds: float = 30.0):
    """
    THE EVICTION CASCADE:
    Finds transcripts in Redis older than 'max_age_seconds', moves them to Qdrant,
    and deletes them from Redis to free up expensive RAM.
    """
    import time
    
    setup_qdrant_collection()
    
    zset_key = f"meeting:{meeting_id}:timeline"
    cutoff_time = time.time() - max_age_seconds
    
    old_records = await redis_client.zrangebyscore(zset_key, 0, cutoff_time, withscores=True)
    
    if not old_records:
        logger.info(f"No stale transcripts found in {meeting_id} for eviction.")
        return 0
    
    points = []
    
    for row, score in old_records:
        try:
            data = json.loads(row)
            raw_text = data.get("text", "")
            speaker = data.get("speaker", "Unknown")
            if not raw_text.strip():
                continue
            # 3. GENERATE VECTOR (Convert the human text into AI Math Coordinates via Gemini!)
            dense_vector = get_real_embedding(raw_text)
            vector_id = str(uuid.uuid4())
        
            point = PointStruct(
                id=vector_id,
                vector=dense_vector,
                payload={
                    # LangChain automatically looks for a 'page_content' field.
                    # We bake the timestamp and speaker directly into the text!
                    "page_content": f"[{time.strftime('%H:%M:%S', time.gmtime(score))}] {speaker}: {raw_text}",
                    "metadata": {
                        "meeting_id": meeting_id,
                        "speaker": speaker,
                        "timestamp": score
                    }
                }
            )
            points.append(point)
        except Exception as e:
            logger.error(f"Error processing row for eviction: {e}")
            
    if points:
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        logger.info(f"Evicted {len(points)} vectors to Qdrant for {meeting_id}!")
        
        await redis_client.zremrangebyscore(zset_key, 0, cutoff_time)
        logger.info(f"Deleted {len(points)} old transcripts from Redis RAM.")
        
    return len(points)
