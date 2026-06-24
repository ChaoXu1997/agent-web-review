/* background.js — Service worker for Agent Web Review */

const DEFAULT_SERVER_URL = "http://localhost:9876";

async function getServerUrl() {
  const { serverUrl } = await chrome.storage.local.get("serverUrl");
  return serverUrl || DEFAULT_SERVER_URL;
}

async function getApiKey() {
  const { apiKey } = await chrome.storage.local.get("apiKey");
  return apiKey || "";
}

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "toggle-inspect-mode") return;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id || !tab.url || tab.url.startsWith("chrome")) return;
  chrome.tabs.sendMessage(tab.id, { action: "toggleInspect" }).catch(() => {
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"],
    }).then(() => {
      chrome.tabs.sendMessage(tab.id, { action: "toggleInspect" });
    });
  });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "getServerUrl") {
    getServerUrl().then(sendResponse);
    return true;
  }
  if (message.action === "setServerUrl") {
    chrome.storage.local.set({ serverUrl: message.url });
    sendResponse({ ok: true });
    return false;
  }
  if (message.action === "getApiKey") {
    getApiKey().then(sendResponse);
    return true;
  }
  if (message.action === "setApiKey") {
    chrome.storage.local.set({ apiKey: message.key });
    sendResponse({ ok: true });
    return false;
  }
});
