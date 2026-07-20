import json
import logging
import uuid
import os
import time
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.redis_store import redis_client

logger = logging.getLogger(__name__)

qdrant_client = QdrantClient(location=":memory:")
COLLECTION_NAME = "meeting_transcripts"


def setup_qdrant_collection():
    """Ensures the Qdrant collection exists before saving data."""
    if not qdrant_client.collection_exists(COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")


def get_real_embedding(text: str) -> List[float]:
    """Generates a 384-dimensional embedding using local HuggingFace MiniLM."""
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return embeddings.embed_query(text)


async def evict_old_transcripts(meeting_id: str, max_age_seconds: float = 30.0):
    """
    THE EVICTION CASCADE — now visibility-aware.

    Reads old chunks from BOTH :admin and :public ZSETs, moves them to Qdrant
    with their visibility tag preserved, then deletes them from Redis.

    Qdrant payload includes 'visibility' so the RAG agent can filter by role.
    """
    setup_qdrant_collection()

    cutoff_time = time.time() - max_age_seconds
    points = []
    evicted_keys = {"admin": [], "public": []}

    for tier in ["admin", "public"]:
        zset_key = f"meeting:{meeting_id}:timeline:{tier}"
        old_records = await redis_client.zrangebyscore(zset_key, 0, cutoff_time, withscores=True)

        for row, score in old_records:
            try:
                data = json.loads(row)
                raw_text = data.get("text", "")
                speaker = data.get("speaker", "Unknown")
                visibility = data.get("visibility", tier)

                if not raw_text.strip():
                    continue

                dense_vector = get_real_embedding(raw_text)
                vector_id = str(uuid.uuid4())

                point = PointStruct(
                    id=vector_id,
                    vector=dense_vector,
                    payload={
                        # LangChain's retriever looks for 'page_content'
                        "page_content": f"[{time.strftime('%H:%M:%S', time.gmtime(score))}] {speaker}: {raw_text}",
                        "metadata": {
                            "meeting_id": meeting_id,
                            "speaker": speaker,
                            "timestamp": score,
                            "visibility": visibility,   # ← KEY: preserved for RAG filtering
                        }
                    }
                )
                points.append(point)
                evicted_keys[tier].append((row, score))

            except Exception as e:
                logger.error(f"Error processing row for eviction: {e}")

    if points:
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info(f"Evicted {len(points)} vectors to Qdrant for {meeting_id}")

        # Clean up Redis — only delete entries that were actually evicted
        for tier, records in evicted_keys.items():
            if records:
                zset_key = f"meeting:{meeting_id}:timeline:{tier}"
                await redis_client.zremrangebyscore(zset_key, 0, cutoff_time)
                logger.info(f"Deleted {len(records)} old entries from {zset_key}")

    return len(points)


def get_qdrant_filter_for_role(meeting_id: str, role: str) -> Filter:
    """
    Returns a Qdrant filter that scopes vector search by meeting + visibility.
    - admin: gets all chunks (admin_only + public)
    - member: gets only public chunks
    """
    conditions = [
        FieldCondition(key="metadata.meeting_id", match=MatchValue(value=meeting_id))
    ]

    if role == "member":
        conditions.append(
            FieldCondition(key="metadata.visibility", match=MatchValue(value="public"))
        )

    return Filter(must=conditions)
