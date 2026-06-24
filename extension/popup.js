/* popup.js — Agent Web Review popup logic */

(async function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const statusDot = $("#statusDot");
  const serverUrlInput = $("#serverUrl");
  const toggleBtn = $("#toggleBtn");
  const commentList = $("#commentList");
  const emptyState = $("#emptyState");
  const clearAllBtn = $("#clearAllBtn");

  let currentTab = null;
  let serverUrl = "";
  let isInspecting = false;
  let apiKey = "";

  /* ---- helpers ---- */

  async function getServerUrl() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ action: "getServerUrl" }, (url) => resolve(url));
    });
  }

  async function getStoredApiKey() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ action: "getApiKey" }, (key) => resolve(key || ""));
    });
  }

  async function apiFetch(path, opts = {}) {
    const url = serverUrl.replace(/\/+$/, "") + path;
    const headers = { "Content-Type": "application/json", ...opts.headers };
    if (apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }
    const res = await fetch(url, { ...opts, headers });
    if (res.status === 204) return null;
    return res.json();
  }

  function setStatus(state) {
    statusDot.className = "status-dot " + state;
  }

  function formatTime(iso) {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function truncate(str, len) {
    return str && str.length > len ? str.slice(0, len) + "..." : str;
  }

  /* ---- init ---- */

  async function init() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    currentTab = tab;

    if (!tab || !tab.url || tab.url.startsWith("chrome")) {
      $(".popup").innerHTML = '<p style="text-align:center;padding:24px;color:#9ca3af;">This page is not supported.</p>';
      return;
    }

    serverUrl = await getServerUrl();
    serverUrlInput.value = serverUrl;

    apiKey = await getStoredApiKey();
    document.getElementById("apiKey").value = apiKey;

    checkHealth();
    loadComments();
  }

  async function checkHealth() {
    setStatus("load");
    try {
      await apiFetch("/api/health");
      setStatus("ok");
    } catch {
      setStatus("err");
    }
  }

  async function loadComments() {
    if (!currentTab) return;
    try {
      const encoded = encodeURIComponent(currentTab.url);
      const comments = await apiFetch("/api/comments?page_url=" + encoded);
      renderComments(comments || []);
    } catch {
      renderComments([]);
    }
  }

  /* ---- render ---- */

  function renderComments(comments) {
    commentList.innerHTML = "";
    if (!comments.length) {
      commentList.appendChild(emptyState);
      emptyState.style.display = "";
      clearAllBtn.style.display = "none";
      return;
    }

    emptyState.style.display = "none";
    clearAllBtn.style.display = "";

    comments.forEach((c, i) => {
      const isResolved = c.status === "resolved";
      const hasShot = Boolean(c.screenshot_b64);
      const item = document.createElement("div");
      item.className = "comment-item" + (isResolved ? " comment-item--resolved" : "");
      const statusClass = isResolved ? "comment-status--resolved" : "comment-status--open";
      const statusLabel = isResolved ? "Resolved" : "Open";
      const shotClass = hasShot ? "comment-shot--yes" : "comment-shot--no";
      const shotLabel = hasShot ? "📷 Screenshot" : "📷 No screenshot";
      const shotTitle = hasShot ? "This comment includes a screenshot" : "No screenshot attached";
      item.innerHTML = `
        <span class="comment-marker">${i + 1}</span>
        <div class="comment-body">
          <div class="comment-text">${escapeHtml(c.comment_text)}</div>
          ${c.element_selector ? `<div class="comment-selector" title="${escapeHtml(c.element_selector)}">${escapeHtml(truncate(c.element_selector, 60))}</div>` : ""}
          <div class="comment-time">${formatTime(c.timestamp)} <span class="comment-status ${statusClass}">${statusLabel}</span><span class="comment-shot ${shotClass}" title="${escapeHtml(shotTitle)}">${shotLabel}</span></div>
        </div>
        <button class="comment-delete" data-id="${c.id}" title="Delete">&times;</button>
      `;
      commentList.appendChild(item);
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  /* ---- events ---- */

  serverUrlInput.addEventListener("change", async () => {
    serverUrl = serverUrlInput.value.trim();
    chrome.runtime.sendMessage({ action: "setServerUrl", url: serverUrl });
    checkHealth();
    loadComments();
  });

  document.getElementById("apiKey").addEventListener("change", async () => {
    apiKey = document.getElementById("apiKey").value.trim();
    chrome.runtime.sendMessage({ action: "setApiKey", key: apiKey });
    checkHealth();
    loadComments();
  });

  toggleBtn.addEventListener("click", async () => {
    if (!currentTab || !currentTab.id) return;
    try {
      await chrome.tabs.sendMessage(currentTab.id, { action: "toggleInspect" });
    } catch {
      await chrome.scripting.executeScript({
        target: { tabId: currentTab.id },
        files: ["content.js"],
      });
      await chrome.tabs.sendMessage(currentTab.id, { action: "toggleInspect" });
    }
    isInspecting = !isInspecting;
    toggleBtn.classList.toggle("active", isInspecting);
    toggleBtn.querySelector(".btn-label").textContent = isInspecting ? "Stop Inspecting" : "Start Inspecting";
  });

  commentList.addEventListener("click", async (e) => {
    const btn = e.target.closest(".comment-delete");
    if (!btn) return;
    const id = btn.dataset.id;
    try {
      await apiFetch("/api/comments/" + id, { method: "DELETE" });
      loadComments();
    } catch { /* ignore */ }
  });

  clearAllBtn.addEventListener("click", async () => {
    if (!currentTab) return;
    try {
      const encoded = encodeURIComponent(currentTab.url);
      await apiFetch("/api/comments?page_url=" + encoded, { method: "DELETE" });
      loadComments();
    } catch { /* ignore */ }
  });

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === "commentsChanged") loadComments();
  });

  init();
})();
