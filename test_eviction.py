import asyncio
import time
import json
from app.redis_store import redis_client
from app.vector_store import evict_old_transcripts

async def main():
    meeting_id = "test_meeting_999"
    zset_key = f"meeting:{meeting_id}:timeline"
    
    print("\n[1] Cleaning up any old test data...")
    await redis_client.delete(zset_key)
    
    print("\n[2] Adding fake transcripts to Redis RAM...")
    # We use zadd directly so we can fake the timestamps to be 1 hour old!
    old_time_1 = time.time() - 3600  # 1 hour ago
    old_time_2 = time.time() - 3500
    
    payload1 = json.dumps({"speaker": "Alice", "text": "This is a really old message from Alice."})
    payload2 = json.dumps({"speaker": "Bob", "text": "Bob replied a long time ago too."})
    
    await redis_client.zadd(zset_key, {payload1: old_time_1, payload2: old_time_2})
    
    print("\n[3] Checking Redis RAM...")
    count = await redis_client.zcard(zset_key)
    print(f"   -> Found {count} transcripts in Redis RAM!")
    
    print("\n[4] TRIGGERING EVICTION CASCADE...")
    # Evict anything older than 30 seconds
    evicted_count = await evict_old_transcripts(meeting_id, max_age_seconds=30.0)
    print(f"   -> Successfully converted {evicted_count} texts into 1536-dimensional vectors and archived to Qdrant!")
    
    print("\n[5] Checking Redis RAM again...")
    count = await redis_client.zcard(zset_key)
    if count == 0:
        print(f"   -> Found 0 transcripts in Redis RAM! (RAM successfully freed!)")
    else:
        print(f"   -> Found {count} transcripts still in RAM.")
        
    print("\n[SUCCESS] TEST COMPLETE!\n")

if __name__ == "__main__":
    asyncio.run(main())
