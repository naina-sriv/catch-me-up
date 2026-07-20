let mediaRecorder = null;
let websocket = null;
let audioStream = null;
let isRecording = false;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_RECORDING") {
        if (!isRecording) {
            startRecording(request.streamId, request.token);
        }
    }
    if (request.action === "STOP_RECORDING") {
        stopRecording();
    }
});

function startRecording(streamId, token) {
    console.log("[CatchMeUp] startRecording called with streamId:", streamId);

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
        
        // Immediately kill video tracks — we only need audio!
        stream.getVideoTracks().forEach(track => {
            track.stop();
            stream.removeTrack(track);
        });

        audioStream = stream;
        isRecording = true;

        websocket = new WebSocket(`ws://localhost:8000/ws/meeting-stream?token=${token}`);

        websocket.onopen = () => {
            console.log("[CatchMeUp] WebSocket connected. Streaming audio...");
            safeNotify(true);

            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && websocket.readyState === WebSocket.OPEN) {
                    websocket.send(event.data);
                }
            };

            mediaRecorder.start(1000);
        };

        websocket.onerror = (error) => {
            console.error("[CatchMeUp] WebSocket Error:", error);
            stopRecording();
        };

        websocket.onclose = (event) => {
            console.log(`[CatchMeUp] WebSocket closed (Code: ${event.code})`);
            stopRecording();
        };
    })
    .catch((err) => {
        // Log the full error details so we can diagnose it!
        console.error("[CatchMeUp] getUserMedia FAILED:", err.name, "|", err.message, "|", err.constraint);
        isRecording = false;
        safeNotify(false);
    });
}

function stopRecording() {
    console.log("[CatchMeUp] Stopping recording...");
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
    }
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.close();
    }

    mediaRecorder = null;
    audioStream = null;
    websocket = null;
    isRecording = false;

    safeNotify(false);
    console.log("[CatchMeUp] Capture stopped. Offscreen document stays alive for next capture.");
    // NOTE: Do NOT call window.close() — keep the offscreen doc alive so there's no delay next time!
}

function safeNotify(state) {
    try {
        chrome.runtime.sendMessage({ action: "SET_RECORDING_STATE", state });
    } catch (e) {
        console.warn("[CatchMeUp] Could not notify background:", e.message);
    }
}
