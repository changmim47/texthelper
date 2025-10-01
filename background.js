chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "openPolishPopup") {
        chrome.windows.create({
            url: chrome.runtime.getURL("popup.html"),
            type: "popup",
            width: 600,
            height: 600
        });
    }
});
