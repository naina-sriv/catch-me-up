[🏠 Back to Roadmap](../ROADMAP.md) | [< Prev: Chunk 9 - Advanced Redis](../chunk_9_advanced_redis/README.md) | [Next: Chunk 11 - Decoupled SSR >](../chunk_11_decoupled_ssr/README.md)

---

# Chunk 10: Client-Side Resiliency (For the CRUD Developer)

## Where You Are Now (The CRUD World)
In a CRUD app, if a user clicks "Submit Form" and their Wi-Fi drops, the browser spins for a bit, throws a generic "Network Error," and the user loses the data they typed. They have to refresh the page and type it all out again.

## Where We Are Going (JavaScript Ring Buffers)
In a real-time streaming app, network flickers happen constantly (e.g., someone walks into an elevator). We cannot just drop the audio recorded during that 5-second dead zone, because it creates a gap in the meeting transcript.

### The Ring Buffer
To handle Edge Case B (Transient Client Disconnection), the Chrome Extension uses a **Bounded Ring Buffer Array**. 
When the extension detects that the WebSocket connection to the server has died, it doesn't throw the audio away. Instead, it starts pushing the raw audio chunks into a JavaScript Array in memory. 

We call it "Bounded" because we set a hard limit (e.g., max 30 seconds of audio) so the browser doesn't run out of RAM. If the array gets full, the oldest data is overwritten (hence, a "Ring"). 

Once the WebSocket reconnects using an exponential backoff strategy, we perform an **Atomic Batch Flush**: we take all the audio trapped in the Ring Buffer and shoot it down the WebSocket to the server so it can catch up.

## How it works in Code

```javascript
// A simple Ring Buffer implementation in the Chrome Extension background script
const MAX_BUFFER_SIZE = 300; // Stores roughly 30 seconds of 100ms chunks
let audioBuffer = [];

let webSocket = new WebSocket("wss://our-server.com/ws/raw-stream");

// Function called every 100ms by the audio processor
function handleNewAudioChunk(chunk) {
    if (webSocket.readyState === WebSocket.OPEN) {
        // Network is good! Send it immediately.
        webSocket.send(chunk);
    } else {
        // Network is down! Cache it in the Ring Buffer.
        if (audioBuffer.length >= MAX_BUFFER_SIZE) {
            // If full, remove the oldest chunk (index 0) to make room
            audioBuffer.shift(); 
        }
        audioBuffer.push(chunk);
    }
}

// When the network comes back online...
webSocket.onopen = () => {
    console.log("Reconnected! Flushing buffer...");
    
    // Atomic Batch Flush: Send all cached data chronologically
    while (audioBuffer.length > 0) {
        // Remove from the start of the array and send
        let cachedChunk = audioBuffer.shift();
        webSocket.send(cachedChunk);
    }
};
```

---

## 📚 Study Guide for this Chunk

### 📺 Watch These First (Conceptual Foundation)
* 🔍 **YouTube:** `What is a Circular Buffer / Ring Buffer in Computer Science?`
* 🔍 **YouTube:** `Handling WebSocket Reconnections gracefully in JavaScript`

### 📖 Read These Next (Deep Implementation)
* 📖 [Wikipedia: Circular Buffer Theory](https://en.wikipedia.org/wiki/Circular_buffer)
* 📖 [MDN: JavaScript Array Methods](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array)

---

[🏠 Back to Roadmap](../ROADMAP.md) | [< Prev: Chunk 9 - Advanced Redis](../chunk_9_advanced_redis/README.md) | [Next: Chunk 11 - Decoupled SSR >](../chunk_11_decoupled_ssr/README.md)
