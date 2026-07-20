let mediaRecorder = null;
let websocket = null;
let audioStream = null;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_RECORDING") {
        startRecording(request.streamId, request.token);
    }
    
    if (request.action === "STOP_RECORDING") {
        stopRecording();
    }
});

function startRecording(streamId, token) {
    // 1. Use the streamId to hook the raw audio buffer via getUserMedia
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
        // Drop the video track immediately to save CPU, as Chrome forces us to request it!
        stream.getVideoTracks().forEach(track => {
            track.stop();
            stream.removeTrack(track);
        });
        
        audioStream = stream;
        
        // 2. Connect to our heavily secured Python WebSocket!
        websocket = new WebSocket(`ws://localhost:8000/ws/meeting-stream?token=${token}`);
        
        websocket.onopen = () => {
            console.log("WebSocket connected. Starting binary streaming.");
            chrome.storage.local.set({ is_recording: true });
            
            // 3. Chunk the audio stream using MediaRecorder
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && websocket.readyState === WebSocket.OPEN) {
                    // Send the binary blob straight into FastAPI!
                    websocket.send(event.data);
                }
            };
            
            // Slice the audio into 1000ms chunks!
            mediaRecorder.start(1000);
        };

        websocket.onerror = (error) => {
            console.error("WebSocket Error:", error);
            stopRecording();
        };
        
        websocket.onclose = (event) => {
            console.log(`WebSocket closed (Code: ${event.code})`);
            stopRecording();
        };
    })
    .catch((err) => {
        console.error("Failed to get user media in offscreen document:", err);
    });
}

function stopRecording() {
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
    window.close(); // Close the offscreen document when done
}
