/* content.js — Agent Web Review content script */
(function () {
  "use strict";

  /* ---- constants ---- */
  const P = "awr";
  const EL = {
    root: P + "-root",
    highlight: P + "-hl",
    hlLabel: P + "-hl-label",
    marker: P + "-marker",
    markerOrphan: P + "-marker--orphan",
    markerResolved: P + "-marker--resolved",
    panel: P + "-panel",
    panelEl: P + "-panel-el",
    panelSel: P + "-panel-sel",
    panelTa: P + "-panel-ta",
    panelBtns: P + "-panel-btns",
    panelSave: P + "-panel-save",
    panelCancel: P + "-panel-cancel",
    panelShot: P + "-panel-shot",
    panelShotPreview: P + "-panel-shot-preview",
    areaSel: P + "-area",
    markerTip: P + "-marker-tip",
  };

  /* ---- state ---- */
  let active = false;
  let hovered = null;
  let comments = [];
  let markerCount = 0;
  let areaSelecting = false;
  let areaStart = null;
  let areaRect = null;
  let serverUrl = "http://localhost:9876";
  let html2canvasLoaded = false;
  let pendingScreenshot = null;
  let sseReconnectTimer = null;
  let eventSource = null;

  /* ---- DOM refs ---- */
  let root = null;
  let hlBox = null;
  let hlLabel = null;
  let panel = null;

  /* ================================================================
   *  Selector generator
   * ================================================================ */
  function getSelector(el) {
    if (el.id) {
      const escaped = CSS.escape(el.id);
      const sel = "#" + escaped;
      if (document.querySelectorAll(sel).length === 1) return sel;
    }
    const parts = [];
    let cur = el;
    while (cur && cur !== document.documentElement) {
      let seg = cur.tagName.toLowerCase();
      if (cur.id) {
        const escaped = CSS.escape(cur.id);
        const sel = "#" + escaped;
        if (document.querySelectorAll(sel).length === 1) {
          parts.unshift(sel);
          break;
        }
        seg += "#" + escaped;
      }
      if (cur.className && typeof cur.className === "string") {
        const cls = cur.className
          .trim()
          .split(/\s+/)
          .filter((c) => c && !c.startsWith(P + "-"))
          .slice(0, 2)
          .map(CSS.escape)
          .join(".");
        if (cls) seg += "." + cls;
      }
      const parent = cur.parentElement;
      if (parent) {
        const sibs = Array.from(parent.children).filter((s) => s.tagName === cur.tagName);
        if (sibs.length > 1) {
          seg += ":nth-of-type(" + (sibs.indexOf(cur) + 1) + ")";
        }
      }
      parts.unshift(seg);
      cur = cur.parentElement;
      if (parts.length > 5) break;
    }
    return parts.join(" > ");
  }

  function getXPath(el) {
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === Node.ELEMENT_NODE) {
      let idx = 1;
      let sib = cur.previousElementSibling;
      while (sib) {
        if (sib.tagName === cur.tagName) idx++;
        sib = sib.previousElementSibling;
      }
      parts.unshift(cur.tagName.toLowerCase() + "[" + idx + "]");
      cur = cur.parentNode;
      if (cur === document) break;
    }
    return "/" + parts.join("/");
  }

  /* ================================================================
   *  Overlay manager
   * ================================================================ */
  function ensureRoot() {
    if (root) return;
    root = document.createElement("div");
    root.id = EL.root;
    document.body.appendChild(root);
  }

  /* ================================================================
   *  Highlight manager
   * ================================================================ */
  function showHighlight(el) {
    if (!hlBox) {
      hlBox = document.createElement("div");
      hlBox.className = EL.highlight;
      root.appendChild(hlBox);
      hlLabel = document.createElement("div");
      hlLabel.className = EL.hlLabel;
      root.appendChild(hlLabel);
    }
    const r = el.getBoundingClientRect();
    Object.assign(hlBox.style, {
      display: "block",
      top: r.top + "px",
      left: r.left + "px",
      width: r.width + "px",
      height: r.height + "px",
    });
    hlLabel.textContent = el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + " " + Math.round(r.width) + "×" + Math.round(r.height);
    Object.assign(hlLabel.style, {
      display: "block",
      top: (r.top - 22) + "px",
      left: r.left + "px",
    });
  }

  function hideHighlight() {
    if (hlBox) hlBox.style.display = "none";
    if (hlLabel) hlLabel.style.display = "none";
  }

  /* ================================================================
   *  Marker manager
   * ================================================================ */
  function addMarker(comment) {
    markerCount++;
    const mk = document.createElement("div");
    mk.className = EL.marker;
    mk.textContent = markerCount;
    mk.dataset.commentId = comment.id;
    mk.dataset.selector = comment.element_selector || "";
    mk.title = comment.comment_text;
    if (comment.status === "resolved") {
      mk.classList.add(EL.markerResolved);
    }
    mk.addEventListener("click", (e) => {
      e.stopPropagation();
      showMarkerTooltip(mk, comment);
    });
    root.appendChild(mk);
    positionMarker(mk);
    return mk;
  }

  function positionMarker(mk) {
    const sel = mk.dataset.selector;
    if (!sel) return;
    try {
      const el = document.querySelector(sel);
      if (el) {
        const r = el.getBoundingClientRect();
        mk.classList.remove(EL.markerOrphan);
        Object.assign(mk.style, {
          display: "flex",
          top: (r.top - 12) + "px",
          left: (r.right - 12) + "px",
        });
        return;
      }
    } catch { /* invalid selector */ }
    mk.classList.add(EL.markerOrphan);
    mk.style.display = "none";
  }

  function repositionAllMarkers() {
    if (!root) return;
    root.querySelectorAll("." + EL.marker).forEach(positionMarker);
  }

  function showMarkerTooltip(mk, comment) {
    removeMarkerTooltip();
    const tip = document.createElement("div");
    tip.className = EL.markerTip;
    tip.textContent = comment.comment_text;
    const r = mk.getBoundingClientRect();
    Object.assign(tip.style, {
      top: (r.bottom + 6) + "px",
      left: r.left + "px",
    });
    root.appendChild(tip);
    setTimeout(() => {
      const close = (e) => {
        if (!tip.contains(e.target)) {
          removeMarkerTooltip();
          document.removeEventListener("mousedown", close, true);
        }
      };
      document.addEventListener("mousedown", close, true);
    }, 0);
  }

  function removeMarkerTooltip() {
    if (!root) return;
    const existing = root.querySelector("." + EL.markerTip);
    if (existing) existing.remove();
  }

  function resolveMarker(commentId) {
    if (!root) return;
    const mk = root.querySelector('.' + EL.marker + '[data-comment-id="' + commentId + '"]');
    if (mk) {
      mk.classList.add(EL.markerResolved);
    }
    /* Update local comment state */
    const c = comments.find((c) => c.id === commentId);
    if (c) c.status = "resolved";
  }

  /* ================================================================
   *  Comment panel — built with DOM API, no innerHTML
   * ================================================================ */
  function openPanel(x, y, elementInfo) {
    closePanel();
    panel = document.createElement("div");
    panel.className = EL.panel;

    if (elementInfo) {
      const elInfo = document.createElement("div");
      elInfo.className = EL.panelEl;
      elInfo.textContent = "<" + elementInfo.tag + ">";
      const selSpan = document.createElement("span");
      selSpan.className = EL.panelSel;
      selSpan.textContent = elementInfo.selector;
      elInfo.appendChild(selSpan);
      panel.appendChild(elInfo);
    }

    const ta = document.createElement("textarea");
    ta.className = EL.panelTa;
    ta.placeholder = "Type your review comment…";
    ta.rows = 3;
    panel.appendChild(ta);

    const btns = document.createElement("div");
    btns.className = EL.panelBtns;

    const shotBtn = document.createElement("button");
    shotBtn.className = EL.panelShot;
    shotBtn.title = "Capture screenshot of element";
    shotBtn.textContent = "📷 Screenshot";

    const cancelBtn = document.createElement("button");
    cancelBtn.className = EL.panelCancel;
    cancelBtn.textContent = "Cancel";

    const saveBtn = document.createElement("button");
    saveBtn.className = EL.panelSave;
    saveBtn.textContent = "Save";

    btns.appendChild(shotBtn);
    btns.appendChild(cancelBtn);
    btns.appendChild(saveBtn);
    panel.appendChild(btns);

    const preview = document.createElement("div");
    preview.className = EL.panelShotPreview;
    panel.appendChild(preview);

    const r = document.documentElement.getBoundingClientRect();
    const px = Math.min(x, r.width - 340);
    const py = Math.min(y + 10, r.height - 260);
    Object.assign(panel.style, {
      display: "block",
      left: Math.max(px, 8) + "px",
      top: Math.max(py, 8) + "px",
    });

    root.appendChild(panel);
    ta.focus();

    saveBtn.addEventListener("click", () => saveComment(elementInfo, ta.value));
    cancelBtn.addEventListener("click", closePanel);
    shotBtn.addEventListener("click", async () => {
      if (!elementInfo || !elementInfo.element) return;
      shotBtn.disabled = true;
      shotBtn.textContent = "Capturing…";
      const b64 = await captureScreenshot(elementInfo.element);
      if (b64) {
        pendingScreenshot = b64;
        preview.textContent = "";
        const img = document.createElement("img");
        img.src = b64;
        img.style.cssText = "max-width:100%;max-height:120px;border-radius:4px;margin-top:6px;border:1px solid #e5e7eb;";
        preview.appendChild(img);
      }
      shotBtn.disabled = false;
      shotBtn.textContent = "📷 Screenshot";
    });

    ta.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        saveComment(elementInfo, ta.value);
      }
      if (e.key === "Escape") closePanel();
    });
  }

  function closePanel() {
    if (panel) {
      panel.remove();
      panel = null;
    }
    pendingScreenshot = null;
  }

  async function saveComment(elementInfo, text) {
    text = text.trim();
    if (!text) return;

    const data = {
      page_url: location.href,
      comment_text: text,
      timestamp: new Date().toISOString(),
      status: "open",
    };

    if (elementInfo) {
      data.element_selector = elementInfo.selector || "";
      data.element_xpath = elementInfo.xpath || "";
      data.element_text = elementInfo.element ? (elementInfo.element.textContent || "").slice(0, 200) : "";
      data.element_html = elementInfo.element ? elementInfo.element.outerHTML.slice(0, 500) : "";
      const r = elementInfo.element.getBoundingClientRect();
      data.area = {
        x: Math.round(r.x),
        y: Math.round(r.y),
        width: Math.round(r.width),
        height: Math.round(r.height),
      };
    } else if (areaRect) {
      data.area = areaRect;
    }

    if (pendingScreenshot) {
      data.screenshot_b64 = pendingScreenshot;
    }

    try {
      const res = await fetch(serverUrl.replace(/\/+$/, "") + "/api/comments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const comment = await res.json();
      comments.push(comment);
      addMarker(comment);
      closePanel();
      chrome.runtime.sendMessage({ action: "commentsChanged" });
    } catch { /* server offline */ }
  }

  /* ================================================================
   *  Screenshot capture via html2canvas
   * ================================================================ */
  async function loadHtml2Canvas() {
    if (html2canvasLoaded) return true;
    if (typeof html2canvas !== "undefined") {
      html2canvasLoaded = true;
      return true;
    }
    return new Promise((resolve) => {
      const s = document.createElement("script");
      s.src = chrome.runtime.getURL("lib/html2canvas.min.js");
      s.onload = () => {
        html2canvasLoaded = true;
        resolve(true);
      };
      s.onerror = () => resolve(false);
      document.head.appendChild(s);
    });
  }

  async function captureScreenshot(element) {
    const ok = await loadHtml2Canvas();
    if (!ok || typeof html2canvas === "undefined") return null;
    try {
      const canvas = await html2canvas(element, {
        useCORS: true,
        allowTaint: false,
        scale: 1,
        backgroundColor: null,
        logging: false,
      });
      return canvas.toDataURL("image/png");
    } catch {
      return null;
    }
  }

  /* ================================================================
   *  Area selection
   * ================================================================ */
  function startAreaSelection(e) {
    areaSelecting = true;
    areaStart = { clientX: e.clientX, clientY: e.clientY, pageX: e.pageX, pageY: e.pageY };
    areaRect = null;
    const sel = document.createElement("div");
    sel.className = EL.areaSel;
    Object.assign(sel.style, {
      display: "none",
      top: e.clientY + "px",
      left: e.clientX + "px",
      width: "0px",
      height: "0px",
    });
    root.appendChild(sel);
  }

  function updateAreaSelection(e) {
    if (!areaSelecting || !areaStart) return;
    const sel = root.querySelector("." + EL.areaSel);
    if (!sel) return;
    const x = Math.min(areaStart.clientX, e.clientX);
    const y = Math.min(areaStart.clientY, e.clientY);
    const w = Math.abs(e.clientX - areaStart.clientX);
    const h = Math.abs(e.clientY - areaStart.clientY);
    Object.assign(sel.style, { display: "block", top: y + "px", left: x + "px", width: w + "px", height: h + "px" });
  }

  function endAreaSelection(e) {
    if (!areaSelecting || !areaStart) return;
    areaSelecting = false;
    const sel = root.querySelector("." + EL.areaSel);
    if (sel) sel.remove();

    const x = Math.min(areaStart.clientX, e.clientX);
    const y = Math.min(areaStart.clientY, e.clientY);
    const w = Math.abs(e.clientX - areaStart.clientX);
    const h = Math.abs(e.clientY - areaStart.clientY);

    if (w < 5 || h < 5) {
      areaStart = null;
      areaRect = null;
      return;
    }

    areaRect = { x: Math.round(x), y: Math.round(y), width: Math.round(w), height: Math.round(h) };
    openPanel(x + w, y, null);
    areaStart = null;
  }

  /* ================================================================
   *  Server client
   * ================================================================ */
  async function loadComments() {
    try {
      const url = serverUrl.replace(/\/+$/, "") + "/api/comments?page_url=" + encodeURIComponent(location.href);
      const res = await fetch(url);
      comments = await res.json();
      comments.forEach((c) => addMarker(c));
    } catch { /* server offline */ }
  }

  function connectSSE() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    eventSource = new EventSource(serverUrl.replace(/\/+$/, "") + "/api/comments/stream");
    eventSource.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "comment_added" && msg.data.page_url === location.href) {
          comments.push(msg.data);
          addMarker(msg.data);
          chrome.runtime.sendMessage({ action: "commentsChanged" });
        } else if (msg.type === "comment_deleted") {
          comments = comments.filter((c) => c.id !== msg.data.id);
          if (root) {
            const mk = root.querySelector('.' + EL.marker + '[data-comment-id="' + msg.data.id + '"]');
            if (mk) mk.remove();
          }
          chrome.runtime.sendMessage({ action: "commentsChanged" });
        } else if (msg.type === "comments_cleared" && msg.data.page_url === location.href) {
          comments = [];
          if (root) root.querySelectorAll("." + EL.marker).forEach((m) => m.remove());
          markerCount = 0;
          chrome.runtime.sendMessage({ action: "commentsChanged" });
        } else if (msg.type === "comment_resolved") {
          resolveMarker(msg.data.id);
          chrome.runtime.sendMessage({ action: "commentsChanged" });
        }
      } catch { /* ignore parse errors */ }
    };
    eventSource.onerror = () => {
      eventSource.close();
      eventSource = null;
      if (active) {
        sseReconnectTimer = setTimeout(connectSSE, 5000);
      }
    };
  }

  function disconnectSSE() {
    if (sseReconnectTimer) {
      clearTimeout(sseReconnectTimer);
      sseReconnectTimer = null;
    }
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }

  /* ================================================================
   *  Event listeners
   * ================================================================ */
  function onMouseMove(e) {
    if (!active || areaSelecting || panel) return;
    if (root && root.contains(e.target)) {
      hideHighlight();
      hovered = null;
      return;
    }
    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el || el === hovered || el === root || root.contains(el)) return;
    hovered = el;
    showHighlight(el);
  }

  function onMouseDown(e) {
    if (!active) return;
    if (e.shiftKey && !panel) {
      e.preventDefault();
      e.stopPropagation();
      startAreaSelection(e);
    }
  }

  function onClick(e) {
    if (!active) return;
    if (root && root.contains(e.target)) return;
    if (areaSelecting) return;

    e.preventDefault();
    e.stopPropagation();

    const el = document.elementFromPoint(e.clientX, e.clientY);
    if (!el || el === root || root.contains(el)) return;

    openPanel(e.clientX, e.clientY, {
      element: el,
      tag: el.tagName.toLowerCase(),
      selector: getSelector(el),
      xpath: getXPath(el),
    });
  }

  function onMouseMoveArea(e) {
    if (areaSelecting) updateAreaSelection(e);
  }

  function onMouseUp(e) {
    if (areaSelecting) endAreaSelection(e);
  }

  function onKeyDown(e) {
    if (e.key === "Escape") {
      closePanel();
      if (areaSelecting) {
        areaSelecting = false;
        if (root) {
          const sel = root.querySelector("." + EL.areaSel);
          if (sel) sel.remove();
        }
        areaStart = null;
      }
    }
  }

  let scrollRaf = false;
  function onScroll() {
    if (scrollRaf) return;
    scrollRaf = true;
    requestAnimationFrame(() => {
      hideHighlight();
      repositionAllMarkers();
      scrollRaf = false;
    });
  }

  /* ---- MutationObserver for marker repositioning ---- */
  let domObserver = null;

  function startDomObserver() {
    if (domObserver) return;
    domObserver = new MutationObserver(() => {
      repositionAllMarkers();
    });
    domObserver.observe(document.body, { childList: true, subtree: true });
  }

  function stopDomObserver() {
    if (domObserver) {
      domObserver.disconnect();
      domObserver = null;
    }
  }

  /* ---- toggle ---- */
  function activate() {
    if (active) return;
    active = true;
    ensureRoot();
    document.addEventListener("mousemove", onMouseMove, true);
    document.addEventListener("mousedown", onMouseDown, true);
    document.addEventListener("click", onClick, true);
    document.addEventListener("mousemove", onMouseMoveArea, true);
    document.addEventListener("mouseup", onMouseUp, true);
    document.addEventListener("keydown", onKeyDown, true);
    document.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onScroll, true);
    document.body.style.cursor = "crosshair";
    loadComments();
    connectSSE();
    startDomObserver();
  }

  function deactivate() {
    if (!active) return;
    active = false;
    document.removeEventListener("mousemove", onMouseMove, true);
    document.removeEventListener("mousedown", onMouseDown, true);
    document.removeEventListener("click", onClick, true);
    document.removeEventListener("mousemove", onMouseMoveArea, true);
    document.removeEventListener("mouseup", onMouseUp, true);
    document.removeEventListener("keydown", onKeyDown, true);
    document.removeEventListener("scroll", onScroll, true);
    window.removeEventListener("resize", onScroll, true);
    document.body.style.cursor = "";
    hideHighlight();
    closePanel();
    disconnectSSE();
    stopDomObserver();
    if (root) {
      const sel = root.querySelector("." + EL.areaSel);
      if (sel) sel.remove();
    }
  }

  function toggle() {
    if (active) deactivate();
    else activate();
  }

  /* ---- message from background/popup ---- */
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === "toggleInspect") toggle();
  });

  /* get server URL from background */
  chrome.runtime.sendMessage({ action: "getServerUrl" }, (url) => {
    if (url) serverUrl = url;
  });
})();
