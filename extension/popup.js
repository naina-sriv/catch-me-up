document.addEventListener("DOMContentLoaded", () => {
    const startBtn = document.getElementById("start-btn");
    const stopBtn = document.getElementById("stop-btn");
    const tokenInput = document.getElementById("token-input");
    const statusText = document.getElementById("status-text");
    const statusIndicator = document.getElementById("status-indicator");

    // Check if we have a saved token
    chrome.storage.local.get(["jwt_token", "is_recording"], (res) => {
        if (res.jwt_token) tokenInput.value = res.jwt_token;
        if (res.is_recording) {
            setRecordingState(true);
        }
    });

    startBtn.addEventListener("click", () => {
        const token = tokenInput.value.trim();
        if (!token) {
            alert("Please enter your JWT Token first!");
            return;
        }

        chrome.storage.local.set({ jwt_token: token });

        // 1. Call chooseDesktopMedia here where we have a UI context!
        chrome.desktopCapture.chooseDesktopMedia(["screen", "window", "audio"], (streamId, options) => {
            if (!streamId) {
                alert("Canceled or no stream selected.");
                return;
            }
            if (!options.canRequestAudioTrack) {
                alert("You must check 'Share audio' in the picker!");
                return;
            }

            // 2. Send streamId and token to the background to spawn the offscreen document
            chrome.runtime.sendMessage({ action: "START_CAPTURE", streamId: streamId, token: token }, (response) => {
                if (response && response.success) {
                    setRecordingState(true);
                } else {
                    alert("Failed to start capture: " + (response?.error || "Unknown error"));
                }
            });
        });
    });

    stopBtn.addEventListener("click", () => {
        chrome.runtime.sendMessage({ action: "STOP_CAPTURE" }, () => {
            setRecordingState(false);
        });
    });

    function setRecordingState(isRecording) {
        if (isRecording) {
            startBtn.disabled = true;
            stopBtn.disabled = false;
            statusText.innerText = "Capturing Audio...";
            statusIndicator.className = "dot green";
        } else {
            startBtn.disabled = false;
            stopBtn.disabled = true;
            statusText.innerText = "Disconnected";
            statusIndicator.className = "dot red";
        }
    }
});
