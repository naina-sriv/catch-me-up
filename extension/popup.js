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

        // Save the token for next time
        chrome.storage.local.set({ jwt_token: token });

        // Tell background.js to start capturing!
        chrome.runtime.sendMessage({ action: "START_CAPTURE", token: token }, (response) => {
            if (response && response.success) {
                setRecordingState(true);
            } else {
                alert("Failed to start capture: " + (response?.error || "Unknown error"));
            }
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
