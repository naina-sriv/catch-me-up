# 🚀 Catch-Me-Up: Learning Roadmap

Welcome to the definitive learning curriculum for the **Meeting Copilot** backend architecture.

👉 **[View the "No Detail Too Small" Glossary](GLOSSARY.md)** - *Read this if you are confused by any small code details like Jinja2, directories, or specific Python functions!*

## 📚 Curriculum Sequence

Welcome! This guide combines the deep-dive theory articles with practical YouTube crash courses. If you are coming from a CRUD background, you shouldn't just read everything at once. Use this structured approach to know **exactly when to watch a video** and **when to read an article** for maximum retention.

---

## 🛑 Step 1: Breaking the Sync Barrier (FastAPI & Async)
**Goal:** Understand how one server thread can handle thousands of audio streams without blocking.
* **Module:** [Chunk 1: FastAPI & Async Python](./chunk_1_fastapi_async/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `mCoding Intro to Async Python and how the event loop works`
* 🔍 **YouTube:** `Tech With Tim FastAPI Tutorial for beginners`

### 📖 Read These Next (Deep Implementation)
* 📖 [RealPython: Async IO in Python](https://realpython.com/async-io-python/)
* 📖 [FastAPI Docs: Concurrency and async / await](https://fastapi.tiangolo.com/async/)

---

## 📞 Step 2: The Real-Time Pipe & Backpressure
**Goal:** Move away from HTTP Request/Response to a continuous WebSocket pipe, using Queues to prevent crashes.
* **Module:** [Chunk 2: WebSockets & Queue Brokers](./chunk_2_websockets_backpressure/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `ByteByteGo WebSockets vs Long Polling System Design`
* 🔍 **YouTube:** `ArjanCodes Asyncio Queues in Python`

### 📖 Read These Next (Deep Implementation)
* 📖 [Understanding Backpressure in Software Architecture](https://medium.com/@jayphelps/backpressure-explained-the-battered-child-of-pragmatism-4490334f1f3c)
* 📖 [Python asyncio.Queue Official Docs](https://docs.python.org/3/library/asyncio-queue.html)

---

## 🧠 Step 3: In-Memory State & Consensus
**Goal:** Learn how to store live meeting transcripts in RAM (Redis) instead of slow hard drives (SQL).
* **Module:** [Chunk 3: Redis Transient Consensus](./chunk_3_redis_transient_consensus/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `ByteByteGo What is Redis and how does it store data in RAM`
* 🔍 **YouTube:** `Hussein Nassau Redis connection pool design architectures`

### 📖 Read These Next (Deep Implementation)
* 📖 [Redis Sorted Sets (ZSET) Explained](https://redis.com/redis-enterprise/data-structures/sorted-sets/)
* 📖 [Redis Official: Introduction to Redis data structures](https://redis.io/docs/data-types/)

---

## 🗺️ Step 4: Meaning Over Keywords (Vector DBs)
**Goal:** Transition from exact text matching to semantic AI meaning matching for long-term memory.
* **Module:** [Chunk 4: Qdrant Vector Eviction](./chunk_4_qdrant_vector_eviction/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `Vector Databases Explained in 5 Minutes vector search visual guide`
* 🔍 **YouTube:** `Qdrant Vector Database Architecture overview`

### 📖 Read These Next (Deep Implementation)
* 📖 [OpenAI: Text Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
* 📖 [Qdrant: Architecture Overview](https://qdrant.tech/documentation/overview/architecture/)

---

## 🤖 Step 5: Google Antigravity Agent Orchestration
**Goal:** Ground the AI in facts and stream the response to the user using the Antigravity SDK.
* **Module:** [Chunk 5: Google Antigravity SDK & RAG](./chunk_5_gemini_agent_orchestration/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `Understanding Agentic AI Workflows and Tool Calling`
* 🔍 **YouTube:** `Server Sent Events SSE vs WebSockets building streaming apps`

### 📖 Read These Next (Deep Implementation)
* 📖 [IBM: What is Retrieval-Augmented Generation (RAG)?](https://research.ibm.com/blog/retrieval-augmented-generation-RAG)
* 📖 [MDN: Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)

---

## 🔒 Step 6: Stateless Security
**Goal:** Secure the WebSocket and API without doing heavy database lookups using Cryptographic math.
* **Module:** [Chunk 6: JWT Scopes Security](./chunk_6_jwt_scopes_security/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `What is a JWT JSON Web Token authentication system design explained`
* 🔍 **YouTube:** `FastAPI Security JWT authentication hands on tutorial`

### 📖 Read These Next (Deep Implementation)
* 📖 [JWT.io: Introduction to JSON Web Tokens](https://jwt.io/introduction)
* 📖 [Auth0: On The Nature of OAuth2's Scopes](https://auth0.com/docs/get-started/apis/scopes)

---

## 🕵️ Step 7: Client-Side Observation
**Goal:** Build the Chrome Extension that invisibly captures audio and watches the HTML DOM for new users.
* **Module:** [Chunk 7: Chrome Extension Audio](./chunk_7_chrome_extension_audio/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `Chrome Extension Developer Tutorial Manifest V3 overview`
* 🔍 **YouTube:** `JavaScript MutationObserver crash course web scraping DOM adjustments`

### 📖 Read These Next (Deep Implementation)
* 📖 [MDN: MutationObserver API](https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver)
* 📖 [Chrome Developers: Audio Capture in Extensions](https://developer.chrome.com/docs/extensions/reference/tabCapture/)

---

## 🎙️ Step 8: Real-Time STT Integration
**Goal:** Connect the backend stream to Deepgram Nova-2 to achieve sub-second live transcription.
* **Module:** [Chunk 8: Real-Time STT Integration](./chunk_8_deepgram_stt/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `Deepgram Nova-2 Architecture Overview`
* 🔍 **YouTube:** `Building a real-time Speech-to-Text WebSocket client`

### 📖 Read These Next (Deep Implementation)
* 📖 [Deepgram Docs: Streaming Audio to the WebSocket API](https://developers.deepgram.com/docs/streaming-overview)
* 📖 [Python Websockets Library Official Documentation](https://websockets.readthedocs.io/en/stable/)

---

## 🚀 Step 9: Advanced Redis State (Whitelists & Absence)
**Goal:** Compute delta-times for absent users and instantly authorize guests using O(1) mathematical lookups.
* **Module:** [Chunk 9: Advanced Redis State](./chunk_9_advanced_redis/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `Redis Hash vs Redis Set performance comparison`
* 🔍 **YouTube:** `Building Real-Time Presence Trackers with Redis Hashes`

### 📖 Read These Next (Deep Implementation)
* 📖 [Redis Documentation: Hashes Tutorial](https://redis.io/docs/data-types/hashes/)
* 📖 [Redis Documentation: Sets Tutorial](https://redis.io/docs/data-types/sets/)

---

## 🛡️ Step 10: Client-Side Resiliency (Ring Buffers)
**Goal:** Cache raw audio inside the browser during network flickers and prevent data loss.
* **Module:** [Chunk 10: Client-Side Resiliency](./chunk_10_client_resiliency/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `What is a Circular Buffer / Ring Buffer in Computer Science?`
* 🔍 **YouTube:** `Handling WebSocket Reconnections gracefully in JavaScript`

### 📖 Read These Next (Deep Implementation)
* 📖 [Wikipedia: Circular Buffer Theory](https://en.wikipedia.org/wiki/Circular_buffer)
* 📖 [MDN: JavaScript Array Methods (Shift, Unshift, Push, Pop)](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array)

---

## 📱 Step 11: Decoupled Server-Side Rendering (SSR)
**Goal:** Serve a secure, reactive dashboard to iOS/Android viewers without building a heavy React frontend.
* **Module:** [Chunk 11: Decoupled SSR](./chunk_11_decoupled_ssr/README.md)

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `Client Side Rendering (CSR) vs Server Side Rendering (SSR) explained visually`
* 🔍 **YouTube:** `FastAPI Jinja2 Templates Crash Course`

### 📖 Read These Next (Deep Implementation)
* 📖 [FastAPI Docs: Using Templates](https://fastapi.tiangolo.com/advanced/templates/)
* 📖 [Jinja2 Documentation: Template Designer Guide](https://jinja.palletsprojects.com/en/3.1.x/templates/)

---
*Ready to begin? Click on **Step 1** above to start your journey.*
