# Agent Web Review

Click on any web page element to add review comments. AI agents (Claude Code, Codex, custom agents) read them via a simple HTTP API and act on your feedback.

Inspired by Codex's "Comment Mode" but works with **any AI agent** through a local HTTP API.

## Quick Start

```bash
# 1. Start the server
python3 server/server.py

# 2. Load the extension in Chrome
#    chrome://extensions → Developer mode → Load unpacked → select /extension

# 3. Open any web page, click the extension icon, start inspecting

# 4. Agents fetch comments via curl:
curl http://localhost:9876/api/comments
```

## Features

- **Inspect mode** — hover to highlight elements, click to add a comment
- **Area selection** — Shift+click to draw a rectangle on any region
- **Element screenshots** — capture screenshots of individual elements
- **Numbered markers** — comments pinned on the page as visual markers
- **Real-time sync** — SSE streaming updates across tabs
- **Keyboard shortcut** — Alt+Shift+C to toggle inspect mode
- **Zero dependencies** — Python stdlib server, no build step for extension

## Architecture

```
┌──────────────┐       HTTP / SSE        ┌──────────────────┐
│  Chrome Ext  │  ◄────────────────────►  │  Python Server   │
│              │                           │  (port 9876)     │
│  content.js  │  POST /api/comments       │                  │
│  popup.js    │  GET  /api/comments       │  storage.py      │
│  background  │  DELETE /api/comments     │  models.py       │
│              │  GET  /api/comments/stream│                  │
└──────────────┘                           └──────────────────┘
                                                    │
                                              JSON file
                                                    │
                                              data/comments.json
                                                    │
                                              ┌─────┴──────┐
                                              │  AI Agents  │
                                              │  (curl)     │
                                              └─────────────┘
```

## API Reference

All endpoints return JSON. CORS enabled for `*`.

### `GET /api/health`

Health check.

```json
{"status": "ok", "version": "1.0.0", "sse_clients": 2}
```

### `POST /api/comments`

Create a new comment.

**Body:**
```json
{
  "page_url": "http://localhost:3000/pricing",
  "element_selector": "#price-card > .amount",
  "element_xpath": "/html/body/main/div[2]/span",
  "element_text": "$29.99",
  "element_html": "<span class=\"amount\">$29.99</span>",
  "screenshot_b64": "data:image/png;base64,...",
  "comment_text": "This price should be $39.99",
  "area": {"x": 100, "y": 200, "width": 150, "height": 30}
}
```

**Response** (201):
```json
{
  "id": "a1b2c3d4",
  "page_url": "http://localhost:3000/pricing",
  "comment_text": "This price should be $39.99",
  "status": "open",
  "timestamp": "2026-04-28T04:00:00+00:00"
}
```

Required fields: `page_url`, `comment_text`.

### `GET /api/comments?page_url=<url>`

List comments, optionally filtered by page URL.

### `DELETE /api/comments/:id`

Delete a single comment. Returns 204 on success, 404 if not found.

### `DELETE /api/comments?page_url=<url>`

Delete all comments for a page. Returns `{"deleted": 3}`.

### `GET /api/comments/stream`

SSE endpoint for real-time updates.

```
data: {"type": "comment_added", "data": {...}}
data: {"type": "comment_deleted", "data": {"id": "..."}}
data: {"type": "comments_cleared", "data": {"page_url": "..."}}
```

## Extension Usage

1. Click the extension icon or press **Alt+Shift+C** to enter inspect mode
2. **Hover** over elements to see a blue highlight with tag info
3. **Click** an element to open the comment panel
4. Type your review and press **Save** (or Ctrl+Enter)
5. Optionally click the camera icon to capture a screenshot of the element
6. **Shift+click** and drag to select a rectangular area instead of an element
7. Press **Escape** to cancel or close panels

## Agent Integration

Any agent that can make HTTP requests can participate:

```bash
# Read pending comments
curl -s http://localhost:9876/api/comments | jq

# Read comments for a specific page
curl -s "http://localhost:9876/api/comments?page_url=http://localhost:3000" | jq

# Delete a comment after acting on it
curl -X DELETE http://localhost:9876/api/comments/<id>

# Stream real-time updates
curl -N http://localhost:9876/api/comments/stream
```

## File Structure

```
├── extension/
│   ├── manifest.json      # Manifest V3 config
│   ├── background.js      # Service worker (message routing)
│   ├── content.js         # Content script (inspect, markers, comments)
│   ├── content.css        # Scoped overlay styles
│   ├── popup.html         # Popup UI
│   ├── popup.js           # Popup logic
│   ├── popup.css          # Popup styles
│   ├── lib/
│   │   └── html2canvas.min.js  # Element screenshot library
│   └── icons/             # SVG icons (16, 48, 128)
├── server/
│   ├── server.py          # HTTP server with SSE
│   ├── storage.py         # JSON file storage
│   ├── models.py          # Comment dataclass
│   └── requirements.txt   # (stdlib only, no deps)
├── tests/
│   ├── test_storage.py    # Storage layer tests
│   └── test_server.py     # API endpoint tests
├── SPEC.md
└── README.md
```

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

## Configuration

- **Server port**: 9876 (auto-finds free port if 9876 is taken)
- **Data directory**: `server/data/` (override with `AWR_DATA_DIR` env var)
- **Server URL**: editable in the extension popup

## Tech Stack

- **Chrome Extension**: Manifest V3, vanilla JavaScript, no build step
- **Python Server**: 3.10+, stdlib only (`http.server`, `json`, `uuid`, `dataclasses`)
- **Screenshots**: html2canvas (bundled, loaded on demand)
- **Storage**: JSON file with atomic writes and thread-safe locking

## Known Limitations

- Cross-origin iframes cannot be inspected
- html2canvas may fail on pages with complex CSS or tainted canvases
- Extension does not work on `chrome://` or `edge://` pages
- JSON file storage is not suitable for high-throughput production use
