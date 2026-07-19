let mediaRecorder = null;
let websocket = null;
let audioStream = null;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_CAPTURE") {
        startCapture(request.token)
            .then(() => sendResponse({ success: true }))
            .catch((err) => {
                console.error("Capture failed", err);
                sendResponse({ success: false, error: err.message });
            });
        return true; // Keep message channel open for async response
    }
    
    if (request.action === "STOP_CAPTURE") {
        stopCapture();
        sendResponse({ success: true });
    }
});

async function startCapture(token) {
    return new Promise((resolve, reject) => {
        // 1. Ask Chrome to let the user pick a desktop window/screen
        // The user MUST check the "Share Audio" box in the popup!
        chrome.desktopCapture.chooseDesktopMedia(["screen", "window", "audio"], (streamId, options) => {
            if (!streamId) {
                return reject(new Error("User canceled the picker or didn't select a stream."));
            }
            if (!options.canRequestAudioTrack) {
                return reject(new Error("Audio was not shared. You must check 'Share audio' in the picker!"));
            }

            // 2. Use the streamId to hook the raw audio buffer via getUserMedia
            navigator.mediaDevices.getUserMedia({
                audio: {
                    mandatory: {
                        chromeMediaSource: "desktop",
                        chromeMediaSourceId: streamId
                    }
                },
                video: false // We don't want video, only the audio!
            })
            .then((stream) => {
                audioStream = stream;
                
                // 3. Connect to our heavily secured Python WebSocket!
                websocket = new WebSocket(`ws://localhost:8000/ws/meeting-stream?token=${token}`);
                
                websocket.onopen = () => {
                    console.log("WebSocket connected. Starting binary streaming.");
                    chrome.storage.local.set({ is_recording: true });
                    
                    // 4. Chunk the audio stream using MediaRecorder
                    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
                    
                    mediaRecorder.ondataavailable = (event) => {
                        if (event.data.size > 0 && websocket.readyState === WebSocket.OPEN) {
                            // Send the binary blob straight into FastAPI!
                            websocket.send(event.data);
                        }
                    };
                    
                    // Slice the audio into 1000ms chunks!
                    mediaRecorder.start(1000);
                    resolve();
                };

                websocket.onerror = (error) => {
                    console.error("WebSocket Error:", error);
                    stopCapture();
                    reject(new Error("WebSocket Connection Failed. Are you sure the Python server is running and the token is valid?"));
                };
                
                websocket.onclose = (event) => {
                    console.log(`WebSocket closed (Code: ${event.code})`);
                    stopCapture();
                };
            })
            .catch((err) => {
                reject(err);
            });
        });
    });
}

function stopCapture() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
    }
    if (websocket) {
        websocket.close();
    }
    
    mediaRecorder = null;
    audioStream = null;
    websocket = null;
    chrome.storage.local.set({ is_recording: false });
    console.log("Capture stopped securely.");
}
