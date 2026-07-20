// Read streamId and token directly from the URL — no async delay!
const params = new URLSearchParams(window.location.search);
const streamId = params.get("streamId");
const token = params.get("token");

const statusText = document.getElementById("status-text");
const infoText = document.getElementById("info-text");
const dot = document.getElementById("dot");

let mediaRecorder = null;
let websocket = null;

function setStatus(msg, info = "") {
    statusText.innerText = msg;
    infoText.innerText = info;
}

if (!streamId || !token) {
    setStatus("Error: Missing params", "Close this window.");
} else {
    startCapture();
}

function startCapture() {
    setStatus("Requesting audio...", "Connecting to system audio stream");

    // Call getUserMedia IMMEDIATELY — streamId is fresh from the URL!
    navigator.mediaDevices.getUserMedia({
        audio: {
            mandatory: {
                chromeMediaSource: "desktop",
                chromeMediaSourceId: streamId
            }
        },
        video: {
            mandatory: {
                chromeMediaSource: "desktop",
                chromeMediaSourceId: streamId
            }
        }
    })
    .then((stream) => {
        console.log("[CatchMeUp] Got stream! Tracks:", stream.getTracks().map(t => t.kind));

        // Drop video tracks — we only want audio!
        stream.getVideoTracks().forEach(track => {
            track.stop();
            stream.removeTrack(track);
        });

        setStatus("Connecting to server...", "Establishing WebSocket");

        websocket = new WebSocket(`ws://localhost:8000/ws/meeting-stream?token=${token}`);

        websocket.onopen = () => {
            console.log("[CatchMeUp] WebSocket connected. Streaming audio...");
            setStatus("🎙️ Recording", "Audio streaming to Catch-Me-Up backend");
            dot.style.background = "#22c55e";

            mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && websocket.readyState === WebSocket.OPEN) {
                    websocket.send(event.data);
                }
            };

            mediaRecorder.start(1000);

            // Notify the background that we are now recording
            chrome.runtime.sendMessage({ action: "SET_RECORDING_STATE", state: true });
        };

        websocket.onerror = (error) => {
            console.error("[CatchMeUp] WebSocket Error:", error);
            setStatus("WebSocket Error", "Check if backend is running");
            stopAndClose();
        };

        websocket.onclose = (event) => {
            console.log(`[CatchMeUp] WebSocket closed (Code: ${event.code})`);
            setStatus("Disconnected", `Server closed connection (${event.code})`);
            stopAndClose();
        };
    })
    .catch((err) => {
        console.error("[CatchMeUp] getUserMedia FAILED:", err.name, "|", err.message);
        setStatus(`Error: ${err.name}`, err.message);
        dot.style.background = "#ef4444";
        dot.style.animation = "none";
        chrome.runtime.sendMessage({ action: "SET_RECORDING_STATE", state: false });
    });
}

function stopAndClose() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
    if (websocket && websocket.readyState === WebSocket.OPEN) websocket.close();
    chrome.runtime.sendMessage({ action: "SET_RECORDING_STATE", state: false });
}

// Listen for stop command from popup
chrome.runtime.onMessage.addListener((request) => {
    if (request.action === "STOP_RECORDING") {
        setStatus("Stopped", "Recording ended.");
        stopAndClose();
        setTimeout(() => window.close(), 1500);
    }
});
