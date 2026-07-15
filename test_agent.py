import asyncio
import time
import json
import os
from app.redis_store import redis_client
from app.vector_store import evict_old_transcripts
from app.agent import ask_copilot

async def main():
    if not os.getenv("GOOGLE_API_KEY"):
        print("\n[WARNING]: You must set GOOGLE_API_KEY in your .env file to run this test!")
        print("Get a free key here: https://aistudio.google.com/app/apikey\n")
        return

    meeting_id = "test_meeting_agent"
    zset_key = f"meeting:{meeting_id}:timeline"
    
    print("\n[1] Preparing a fake meeting...")
    await redis_client.delete(zset_key)
    
    # Fake a meeting where Alice and Bob discussed a secret launch code
    old_time_1 = time.time() - 3600
    old_time_2 = time.time() - 3500
    
    payload1 = json.dumps({"speaker": "Alice", "text": "Bob, the secret launch code for the new project is 'APOLLO-99'."})
    payload2 = json.dumps({"speaker": "Bob", "text": "Understood Alice. I will make sure nobody else finds out about APOLLO-99."})
    
    await redis_client.zadd(zset_key, {payload1: old_time_1, payload2: old_time_2})
    
    print("\n[2] Evicting meeting to Qdrant Vector DB...")
    await evict_old_transcripts(meeting_id, max_age_seconds=10.0)
    
    print("\n[3] Interrogating the LangChain Copilot...")
    # Testing the MOM duration-specific logic!
    question = "I missed the last 5 minutes of the meeting. Can you summarize what happened?"
    print(f"\n[You]: {question}")
    
    # This will use LangChain to retrieve the vectors from Qdrant and pass them to Gemini!
    try:
        answer = await ask_copilot(meeting_id, question)
        print(f"\n[Copilot]:\n{answer}")
    except Exception as e:
        print(f"\n[ERROR]: Gemini API issue. Please ensure your API key is valid and has access to Gemini 1.5 Flash. Details: {e}")
    
    print("\n[SUCCESS] AGENT TEST COMPLETE!\n")

if __name__ == "__main__":
    asyncio.run(main())
