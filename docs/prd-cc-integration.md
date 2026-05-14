# PRD: Claude Code MCP Integration

## Problem Statement

Users can review web pages by adding comments through the Chrome extension, but there is no streamlined way to pass those comments to Claude Code for action. The current agent launch mechanism starts a separate Hermes process, which is a different workflow from the user's active CC session. Users must manually communicate review feedback to CC, breaking the review-fix-verify loop.

## Solution

Integrate Claude Code as the primary agent for processing review comments via the existing MCP protocol. CC reads comments through MCP tools using the project's working directory as the lookup key, modifies source code based on the review feedback, and resolves comments when done. The extension reflects resolved status in real-time via SSE. A new `/awr-setup` skill automates project URL-to-directory mapping registration.

## User Stories

1. As a developer, I want CC to read my web review comments through MCP tools, so that I don't have to manually describe what needs changing
2. As a developer, I want to tell CC "process web comments" and have it find all open comments for the current project, so that the workflow is a single natural language command
3. As a developer, I want CC to automatically resolve comments as it fixes them, so that I can see real-time progress in the browser
4. As a developer, I want resolved comment markers to look different from open ones, so that I can visually track which issues are done
5. As a developer, I want the extension popup to distinguish open and resolved comments, so that I can manage the review status
6. As a developer, I want a `/awr-setup` skill that detects my dev server port and registers the project mapping, so that I don't have to manually configure URL-to-directory mappings
7. As a developer, I want CC to locate source code from element HTML and selectors without source maps, so that the system works with any project setup
8. As a developer, I want the `/awr-setup` skill to work with common frameworks (Vite, Next.js, CRA, etc.), so that it covers most of my projects

## Implementation Decisions

- **CC integration via MCP protocol**: CC connects to the AWR MCP server as a standard MCP client. No new processes to launch, no special communication channel. CC reads comments, modifies code, resolves comments — all through existing MCP tools plus one new parameter.

- **`awr_get_comments` gains `project_path` parameter**: The MCP tool accepts an optional `project_path` string. When provided, the server looks up all page URLs mapped to that project path, then returns all open comments across those URLs. This means CC passes its CWD and gets relevant comments without knowing the browser URL.

- **Project storage gains reverse lookup**: `project_storage.py` adds a `get_urls_by_project_path(path) -> list[str]` function. Given a local filesystem path, returns all registered page URLs for that project. Handles partial matches (e.g., querying `/home/user/project` matches mappings for `/home/user/project/`).

- **Remove `/api/agent/launch` endpoint**: The Hermes-based agent launch is deleted entirely from `server.py`. The MCP path replaces it. Related test file `test_agent_launch.py` is also removed.

- **Resolved comments visual distinction in content script**: Comment markers on the page change appearance when resolved — open markers stay as current red numbered circles, resolved markers become grey with a green checkmark overlay. No new UI, just a CSS change driven by SSE `comment_resolved` events already being broadcast.

- **Popup comment list shows status**: The popup UI distinguishes open and resolved comments in the list — resolved comments are styled with strikethrough or muted color. The popup already fetches and displays comments; this is a display-only change.

- **New `/awr-setup` skill**: A Claude Code skill that: (1) reads project config files (`vite.config.*`, `next.config.*`, `package.json` scripts, etc.) to detect the dev server port, (2) calls `POST /api/projects` on the AWR server to register the mapping between `http://localhost:<port>` and the current working directory. The skill is manually triggered by the user. It needs the AWR server URL (default `http://localhost:9876`).

- **CLAUDE.md AWR workflow section**: Each project that uses AWR should add a section to its CLAUDE.md describing the workflow: when the user says "process web comments", call `awr_get_comments(project_path=<CWD>)`, read each comment's `element_html` and `comment_text` to locate the source component, make changes, then call `awr_resolve_comment(comment_id)` for each fixed comment.

- **MCP tool `awr_get_comments` return format change**: When called with `project_path`, the response includes the `page_url` for each comment so CC knows which page it belongs to. The existing fields (`element_html`, `element_selector`, `element_text`, `comment_text`, `id`) are sufficient for CC to locate and fix source code.

## Testing Decisions

- **What makes a good test**: Test external behavior (API responses, MCP tool outputs) not implementation details (storage internals). Tests should verify the contract between components.

- **Modules to test**:
  - `project_storage.py` reverse lookup — test `get_urls_by_project_path` with exact matches, partial matches, no matches, and multiple URLs per project
  - `awr_get_comments` MCP tool with `project_path` parameter — test that it correctly uses reverse lookup to find comments, handles missing project path, and returns comments with page_url included

- **Prior art**: Existing tests in `test_storage.py` and `test_mcp_server.py` use the same pattern — direct function calls with mock storage, asserting on return values.

## Out of Scope

- Extension connection status detection (CC is not a persistent process)
- Draft/submitted comment states (comments are immediately available)
- Submit button in extension (CC is manually triggered)
- Copy summary button (CC reads via MCP directly)
- Source map integration for precise file/line mapping
- Push notifications from server to CC (MCP is request-response)
- Multi-user or multi-project simultaneous sessions

## Further Notes

- The user's typical workflow is: CC generates a page → user opens in browser → user reviews and adds comments → user tells CC to process → CC reads and fixes → user refreshes to verify
- CC already has strong code understanding of projects it works in, so element HTML + selector is sufficient for source file location without source maps
- The `/awr-setup` skill is project-agnostic and can be installed globally in `~/.claude/skills/`
