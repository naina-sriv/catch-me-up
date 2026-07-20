chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_CAPTURE") {
        const { streamId, token } = request;

        // Build the recorder URL with streamId and token as query params.
        // This passes the streamId instantly — no async delay that would expire it!
        const recorderUrl = chrome.runtime.getURL(
            `recorder.html?streamId=${encodeURIComponent(streamId)}&token=${encodeURIComponent(token)}`
        );

        chrome.windows.create({
            url: recorderUrl,
            type: "popup",
            width: 330,
            height: 100,
            focused: false  // Don't steal focus from the user
        }, (win) => {
            chrome.storage.local.set({ recorder_window_id: win.id });
            sendResponse({ success: true });
        });

        return true; // Keep channel open for async response
    }

    if (request.action === "STOP_CAPTURE") {
        // Tell the recorder window to stop
        chrome.runtime.sendMessage({ action: "STOP_RECORDING" });

        // Also close the window after a short delay
        chrome.storage.local.get("recorder_window_id", (res) => {
            if (res.recorder_window_id) {
                setTimeout(() => {
                    chrome.windows.remove(res.recorder_window_id, () => {
                        chrome.storage.local.remove("recorder_window_id");
                    });
                }, 1800);
            }
        });

        sendResponse({ success: true });
    }

    if (request.action === "SET_RECORDING_STATE") {
        chrome.storage.local.set({ is_recording: request.state });
    }
});
