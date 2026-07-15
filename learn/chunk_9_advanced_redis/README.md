[🏠 Back to Roadmap](../ROADMAP.md) | [< Prev: Chunk 8 - Deepgram STT](../chunk_8_deepgram_stt/README.md) | [Next: Chunk 10 - Client Resiliency >](../chunk_10_client_resiliency/README.md)

---

# Chunk 9: Advanced Redis State (For the CRUD Developer)

## Where You Are Now (The CRUD World)
In CRUD, if you want to know if a user is invited to a meeting, you run a SQL query: `SELECT * FROM invitations WHERE user_id = 5 AND meeting_id = 10`. This requires establishing a database connection, parsing the SQL, executing it, and returning the result. 
If you want to track when a user was last online, you update a row: `UPDATE users SET last_seen = NOW() WHERE id = 5`. 
Doing this 100 times a second for every audio chunk will crash a SQL database.

## Where We Are Going (Redis O(1) Lookups & Delta Tracking)
Because Meeting Copilot processes thousands of events a second, we need validation that happens in less than a millisecond. We use advanced Redis data structures to achieve this.

### O(1) Whitelists (Redis Sets - SADD / SISMEMBER)
Before the meeting starts, the Admin adds invited emails to a Redis **Set**. A Set is a mathematical concept that only holds unique items. When a user tries to connect, we ask Redis: "Is this email in the set?" (`SISMEMBER`). Because of how Sets are built in RAM, Redis can answer this question instantly ($O(1)$ time complexity), regardless of whether there are 10 users or 10,000 users invited.

### Absence Tracking (Redis Hashes - HSET)
To handle Edge Case C (a user drops offline and reconnects), we need to know exactly when they left so we can summarize what they missed. We use a Redis **Hash** (like a Python dictionary) to store `user_email: last_seen_timestamp`. We continuously update this as long as they are connected.

## How it works in Code

```python
from redis import asyncio as aioredis
import time

redis_client = aioredis.from_url("redis://localhost:6379", decode_responses=True)

# --- 1. O(1) Invitation Walls ---
async def check_invitation(meeting_id: str, email: str) -> bool:
    whitelist_key = f"meeting:{meeting_id}:invited"
    
    # SISMEMBER checks if the email exists in the Set. This takes < 1ms.
    is_invited = await redis_client.sismember(whitelist_key, email)
    return is_invited

# --- 2. Absence Tracking ---
async def update_last_seen(meeting_id: str, email: str):
    hash_key = f"meeting:{meeting_id}:active_users"
    
    # HSET updates the dictionary. We set the user's email to the current timestamp.
    await redis_client.hset(hash_key, key=email, value=time.time())

async def get_missed_time_gap(meeting_id: str, email: str) -> float:
    hash_key = f"meeting:{meeting_id}:active_users"
    last_seen = await redis_client.hget(hash_key, key=email)
    
    if last_seen:
        # Calculate exactly how many seconds they missed
        return time.time() - float(last_seen)
    return 0.0
```

---

## 📚 Study Guide for this Chunk

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `Redis Hash vs Redis Set performance comparison`
* 🔍 **YouTube:** `Building Real-Time Presence Trackers with Redis Hashes`

### 📖 Read These Next (Deep Implementation)
* 📖 [Redis Documentation: Hashes Tutorial](https://redis.io/docs/data-types/hashes/)
* 📖 [Redis Documentation: Sets Tutorial](https://redis.io/docs/data-types/sets/)

---

[🏠 Back to Roadmap](../ROADMAP.md) | [< Prev: Chunk 8 - Deepgram STT](../chunk_8_deepgram_stt/README.md) | [Next: Chunk 10 - Client Resiliency >](../chunk_10_client_resiliency/README.md)
