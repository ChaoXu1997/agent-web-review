# Agent Web Review — Chrome Extension + Local Server

## Goal
Build a tool that lets users click on web page elements to add review comments, which AI agents (Hermes, Claude Code, Codex) can then read and act on. Similar to Codex's "Comment Mode" but works with any AI agent via a local HTTP API.

## Architecture

### 1. Chrome Extension (Manifest V3)
- **Content Script** injected into any page
- When activated (click extension icon or keyboard shortcut):
  - Enters "inspect mode" — hovering highlights elements with a blue outline
  - Clicking an element opens a comment popup near the element
  - User types a comment and submits
  - Comment is pinned on the page as a numbered marker (like GitHub review comments)
  - Comment data (element selector, XPath, screenshot of element, comment text, page URL) is POSTed to local server
- **Popup** shows:
  - Toggle inspect mode on/off
  - List of comments on current page
  - Server connection status
- Comments persist visually on the page until cleared
- Support area selection (Shift+click to draw a rectangle)

### 2. Local Python Server (port 9876)
- `POST /api/comments` — receive a new comment from extension
- `GET /api/comments?page_url=<url>` — get comments for a page
- `DELETE /api/comments/:id` — delete a comment
- `DELETE /api/comments?page_url=<url>` — clear all comments for a page
- `GET /api/comments/stream` — SSE endpoint for real-time comment notifications
- `GET /api/health` — health check
- Comments stored as JSON in a file (no database needed)
- Each comment contains:
  ```json
  {
    "id": "uuid",
    "page_url": "http://localhost:3000/pricing",
    "element_selector": "#pricing-card > .price",
    "element_xpath": "/html/body/main/div[2]/div[1]/span",
    "element_text": "$29.99",
    "element_html": "<span class=\"price\">$29.99</span>",
    "screenshot_b64": "data:image/png;base64,...",
    "comment": "This price should be $39.99",
    "area": {"x": 100, "y": 200, "width": 150, "height": 30},
    "timestamp": "2026-04-28T04:00:00Z",
    "status": "open"
  }
  ```

### 3. Agent Integration
- Any agent can `curl http://localhost:9876/api/comments` to get pending comments
- Agent reads the element info + comment, makes code changes, then DELETE the comment
- No special SDK needed — just HTTP

## Technical Requirements
- Chrome Extension: Manifest V3, plain JS (no build step needed)
- Python Server: Python 3.10+, use only stdlib (http.server, json, uuid, dataclasses)
- Content script CSS must be scoped to avoid breaking host pages
- Extension icons: generate simple colored SVG icons
- Keyboard shortcut: Alt+Shift+C to toggle inspect mode

## File Structure
```
agent-web-review/
├── extension/
│   ├── manifest.json
│   ├── background.js       (service worker)
│   ├── content.js           (main inspect + comment logic)
│   ├── content.css          (injected styles)
│   ├── popup.html           (popup UI)
│   ├── popup.js             (popup logic)
│   └── icons/               (SVG/PNG icons)
├── server/
│   ├── server.py            (local HTTP server)
│   └── requirements.txt     (empty or minimal)
├── README.md                (usage instructions)
└── SPEC.md                  (this file)
```

## Deliverables
1. Fully working Chrome extension
2. Fully working Python server
3. README with installation and usage instructions
4. Test by running server, loading extension, adding comments, reading via curl
