chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "START_CAPTURE") {
        setupOffscreenDocument(request)
            .then(() => sendResponse({ success: true }))
            .catch((err) => {
                console.error("Capture failed", err);
                sendResponse({ success: false, error: err.message });
            });
        return true; // Keep message channel open for async response
    }
    
    if (request.action === "STOP_CAPTURE") {
        // Forward stop request to the offscreen document
        chrome.runtime.sendMessage({ action: "STOP_RECORDING" });
        sendResponse({ success: true });
    }
});

async function setupOffscreenDocument(request) {
    const existingContexts = await chrome.runtime.getContexts({
        contextTypes: ['OFFSCREEN_DOCUMENT']
    });

    if (existingContexts.length === 0) {
        // Create the offscreen document
        await chrome.offscreen.createDocument({
            url: 'offscreen.html',
            reasons: ['USER_MEDIA'],
            justification: 'Recording system audio for Meeting Copilot'
        });
    }

    // Now forward the streamId and token to the offscreen document to actually start capturing
    chrome.runtime.sendMessage({
        action: "START_RECORDING",
        streamId: request.streamId,
        token: request.token
    });
}
