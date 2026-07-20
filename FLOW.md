# 🗺️ Catch-Me-Up: Complete System Flow

> All diagrams below are Mermaid. Open this file in any Mermaid-compatible viewer (GitHub, VSCode Markdown Preview, etc.)

---

## 1. Audio Ingestion Flow
*How audio gets from a participant's desktop into the dual Redis ZSETs*

```mermaid
sequenceDiagram
    participant EXT as Chrome Extension
    participant BG as Background.js
    participant REC as Recorder Window
    participant API as FastAPI /ws/meeting-stream
    participant DG as Deepgram STT
    participant REDIS as Redis

    EXT->>EXT: User clicks Start Capture
    EXT->>EXT: chooseDesktopMedia() → streamId
    BG->>REC: Open recorder.html?streamId=...&token=...
    REC->>REC: getUserMedia(streamId) — INSTANT, no expiry delay
    REC->>REC: Drop video tracks, keep audio only
    REC->>API: WebSocket connect with JWT token

    API->>API: verify_token(token) — decode role, meeting_id, joined_at
    API->>API: Check scope "ingest:stream" ✅
    API->>REDIS: heartbeat_node(meeting_id, user_id)
    API->>REDIS: Init meeting config if first node
    API->>DG: Connect to Deepgram wss://

    loop Every 1000ms
        REC->>API: Binary audio chunk (webm/opus)
        API->>API: asyncio.Queue.put(chunk) — backpressure buffer
        API-->>DG: Worker drains queue → send to Deepgram
        DG-->>API: JSON transcript result
        API->>REDIS: get_meeting_visibility(meeting_id)
        REDIS-->>API: "public" or "admin_only"
        API->>REDIS: commit_timeline(id, speaker, text, visibility)
        Note over REDIS: Always writes to :admin ZSET<br>Writes to :public ZSET only if visibility="public"
        API->>REDIS: heartbeat_node() refresh
    end

    REC->>API: WebSocket disconnect
    API->>API: Drain queue → close Deepgram socket
```

---

## 2. Access Control: Who Reads What
*How the dual ZSET model enforces role-based access*

```mermaid
flowchart TD
    USER([User requests transcript]) --> JWT{Verify JWT}
    JWT -->|Invalid / Expired| E401[401 Unauthorized]
    JWT -->|Valid| SCOPE{Has read:transcript scope?}
    SCOPE -->|No| E403[403 Forbidden]
    SCOPE -->|Yes| ROLE{Role in JWT?}

    ROLE -->|admin| ADMIN_KEY["Query :timeline:admin ZSET\nfrom score = 0 (full history)"]
    ROLE -->|member| PUBLIC_CFG["Read public_opened_at\nfrom meeting config"]

    PUBLIC_CFG --> CALC["start_time = max(joined_at, public_opened_at)"]
    CALC --> MEMBER_KEY["Query :timeline:public ZSET\nfrom score = start_time"]

    ADMIN_KEY --> RESULTS["Return scoped transcript"]
    MEMBER_KEY --> RESULTS

    style E401 fill:#ef4444,color:white
    style E403 fill:#f97316,color:white
    style ADMIN_KEY fill:#8b5cf6,color:white
    style MEMBER_KEY fill:#3b82f6,color:white
    style RESULTS fill:#22c55e,color:white
```

---

## 3. Meeting Visibility Toggle
*How an admin controls what members can see, in real-time*

```mermaid
sequenceDiagram
    participant ADMIN as Admin User
    participant API as FastAPI
    participant REDIS as Redis
    participant ZSET_A as :timeline:admin
    participant ZSET_P as :timeline:public

    Note over ZSET_A,ZSET_P: T=0 — Meeting starts (toggle OFF by default)

    loop Admin-only discussion (T=0 → T=5min)
        API->>ZSET_A: commit(text, visibility="admin_only")
        Note over ZSET_P: :public ZSET stays empty
    end

    ADMIN->>API: PATCH /meetings/{id}/toggle-public {is_public: true}
    API->>API: require_role("admin") ✅
    API->>REDIS: hset config public_transcript = "true"
    API->>REDIS: hset config public_opened_at = NOW (recorded once, forever)

    Note over ZSET_A,ZSET_P: T=5min — Meeting opened to public

    loop Public discussion (T=5min onwards)
        API->>ZSET_A: commit(text, visibility="public")
        API->>ZSET_P: commit(text, visibility="public")
        Note over ZSET_A,ZSET_P: Both ZSETs now receive chunks
    end

    Note over ZSET_A,ZSET_P: Late admin joins at T=8min<br>Sees :admin from T=0 ✅<br>Late member joins at T=7min<br>Sees :public from max(7min, 5min)=7min ✅
```

---

## 4. Eviction Cascade → Visibility-Aware Qdrant
*How old Redis data is migrated to Qdrant without losing access control*

```mermaid
flowchart LR
    subgraph REDIS["Redis (Hot Storage)"]
        A[":admin ZSET\n[ts=0..cutoff]"]
        P[":public ZSET\n[ts=0..cutoff]"]
    end

    subgraph EVICT["Eviction Cascade Worker"]
        READ["Read old chunks from\nboth ZSETs"]
        EMBED["Generate 384-dim\nHuggingFace embedding"]
        TAG["Preserve visibility tag\nin Qdrant payload metadata"]
        UPSERT["Upsert PointStruct\nto Qdrant"]
        DEL["zremrangebyscore\nfrom both ZSETs"]
    end

    subgraph QDRANT["Qdrant (Cold Storage)"]
        V1["Vector: 'admin said X'\nmetadata.visibility = admin_only"]
        V2["Vector: 'member discussed Y'\nmetadata.visibility = public"]
    end

    A --> READ
    P --> READ
    READ --> EMBED --> TAG --> UPSERT --> DEL
    UPSERT --> V1
    UPSERT --> V2
    DEL -->|Frees RAM| REDIS

    style V1 fill:#8b5cf6,color:white
    style V2 fill:#3b82f6,color:white
```

---

## 5. "Catch Me Up" RAG Pipeline
*How the AI generates a scoped summary without leaking admin content*

```mermaid
sequenceDiagram
    participant USER as Member/Admin
    participant API as FastAPI /ask
    participant AGENT as LangChain Agent
    participant QDRANT as Qdrant VectorDB
    participant GEMINI as Google Gemini

    USER->>API: POST /meetings/{id}/ask\n{"question": "what did I miss?"}
    API->>API: verify_token → role="member", joined_at=T7

    API->>AGENT: ask_copilot(meeting_id, question, role="member")

    AGENT->>AGENT: Build Qdrant filter:\nmeeting_id=X AND visibility=public

    AGENT->>QDRANT: ANN similarity search\nwith role-scoped filter
    Note over QDRANT: Admin-only vectors physically<br>excluded from search results
    QDRANT-->>AGENT: Top-6 relevant public transcript chunks

    AGENT->>GEMINI: System prompt + chunks as context\n+ user question
    Note over GEMINI: Prompt: "Never hint at content<br>the user cannot access"
    GEMINI-->>AGENT: Scoped summary response

    AGENT-->>API: answer text
    API-->>USER: {"answer": "...", "scoped_to": "member"}
```

---

## 6. Active Node Redundancy
*How multiple ingestion nodes provide fault-tolerance*

```mermaid
flowchart TD
    subgraph NODES["Ingestion Nodes (any participant with JWT)"]
        N1["🎙️ Alice (Admin)\nheartbeat every chunk"]
        N2["🎙️ Bob (Member)\nheartbeat every chunk"]
        N3["🎙️ Carol (Member)\nheartbeat every chunk"]
    end

    subgraph REDIS["Redis Active Nodes"]
        HB["meeting:X:active_nodes\nalice: 1721456100\nbob: 1721456098\ncarol: 1721456102"]
    end

    N1 -->|Binary audio| API
    N2 -->|Binary audio| API
    N3 -->|Binary audio| API

    API["FastAPI WebSocket"] --> DG["Deepgram STT"]
    API --> HB

    DG --> ZSET["Redis Dual ZSETs\n(deduplicated by timestamp score)"]

    N1 -.->|"Network drop ❌"| DROPPED["Alice drops at T=10min"]
    DROPPED --> REDIS_TTL["alice heartbeat expires\nafter 20s → auto-removed"]

    N2 -->|Continues streaming| API
    N3 -->|Continues streaming| API

    NOTE["✅ Bob + Carol cover the meeting\nZero transcript gaps"]

    style DROPPED fill:#ef4444,color:white
    style NOTE fill:#22c55e,color:white
```

---

## 7. JWT Lifecycle
*From authentication to access control enforcement*

```mermaid
flowchart LR
    A["User authenticates\n(Manual token or Discord Bot)"] --> B["create_access_token()\n\nusername, role, meeting_id\njoined_at = NOW\nscope = 'ingest:stream read:transcript'\nexp = NOW + 24h"]

    B --> C["Signed JWT\n(HS256)"]

    C --> D{Request type}

    D -->|"WebSocket\n/ws/meeting-stream"| E["verify_token()\n→ check scope 'ingest:stream'\n→ extract meeting_id\n→ register heartbeat"]

    D -->|"HTTP GET\n/summary/{id}"| F["verify_token()\n→ read role\n→ read joined_at\n→ query correct ZSET"]

    D -->|"HTTP POST\n/meetings/{id}/ask"| G["verify_token()\n→ read role\n→ pass to RAG filter"]

    D -->|"PATCH\n/toggle-public"| H["require_role('admin')\n→ reject if role ≠ admin"]

    style C fill:#f59e0b,color:black
    style H fill:#ef4444,color:white
```
