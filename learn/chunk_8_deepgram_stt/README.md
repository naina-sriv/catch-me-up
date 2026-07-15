[🏠 Back to Roadmap](../ROADMAP.md) | [< Prev: Chunk 7 - Chrome Ext Audio](../chunk_7_chrome_extension_audio/README.md) | [Next: Chunk 9 - Advanced Redis >](../chunk_9_advanced_redis/README.md)

---

# Chunk 8: Real-Time STT Integration (For the CRUD Developer)

## Where You Are Now (The CRUD World)
In a CRUD app, when a user uploads an audio file (like an MP3), your server usually saves it to disk (or AWS S3), and then maybe triggers a background job to transcribe it entirely. This is slow and batch-oriented. The user waits until the whole file is processed.

## Where We Are Going (Real-Time AI Streaming)
In Meeting Copilot, audio is never "finished." It streams continuously. We cannot wait for the meeting to end to transcribe it. 

To achieve sub-second transcription latency, we use **Deepgram Nova-2**. Deepgram allows us to open a *Client-Side WebSocket* from our FastAPI server directly to their AI engine. As soon as our server receives a 100ms chunk of audio from the user (which we put in our `asyncio.Queue` in Chunk 2), a background worker immediately plucks it out and forwards it to Deepgram over this open pipe. Deepgram's AI processes it instantly and pushes text back to us over the same pipe.

## How it works in Code

```python
import websockets
import asyncio

async def deepgram_worker(internal_audio_queue: asyncio.Queue, meeting_id: str):
    # We open a WebSocket connection to Deepgram's AI Engine
    url = "wss://api.deepgram.com/v1/listen?model=nova-2&encoding=webm"
    headers = {"Authorization": "Token YOUR_DEEPGRAM_API_KEY"}
    
    async with websockets.connect(url, extra_headers=headers) as dg_socket:
        
        # Task 1: Keep grabbing audio chunks from our bucket and sending to Deepgram
        async def send_audio():
            while True:
                audio_chunk = await internal_audio_queue.get()
                await dg_socket.send(audio_chunk)
                internal_audio_queue.task_done()
                
        # Task 2: Listen for Deepgram sending text transcripts back
        async def receive_transcripts():
            while True:
                response = await dg_socket.recv()
                # Here, we would save the transcript to Redis (Chunk 3)
                print(f"Deepgram says: {response}")
                
        # Run both tasks concurrently so we can send and receive at the same time
        await asyncio.gather(send_audio(), receive_transcripts())
```

---

## 📚 Study Guide for this Chunk

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `Deepgram Nova-2 Architecture Overview`
* 🔍 **YouTube:** `Building a real-time Speech-to-Text WebSocket client`

### 📖 Read These Next (Deep Implementation)
* 📖 [Deepgram Docs: Streaming Audio](https://developers.deepgram.com/docs/streaming-overview)
* 📖 [Python Websockets Library](https://websockets.readthedocs.io/en/stable/)

---

[🏠 Back to Roadmap](../ROADMAP.md) | [< Prev: Chunk 7 - Chrome Ext Audio](../chunk_7_chrome_extension_audio/README.md) | [Next: Chunk 9 - Advanced Redis >](../chunk_9_advanced_redis/README.md)
