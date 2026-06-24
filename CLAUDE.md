## Agent skills

### Issue tracker

Issues tracked as local markdown files under `.scratch/<feature>/`; external PRs are not a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: CONTEXT.md at repo root, ADRs in docs/adr/. See `docs/agents/domain.md`.

## AWR Workflow — Processing Web Review Comments

When the user says "process web comments", "fix web reviews", or similar:

1. **Get comments**: Call `awr_get_comments(project_path="<current working directory>")` to fetch all open review comments for this project
2. **Read each comment**: Each comment contains:
   - `comment_text` — what the reviewer wants changed
   - `element_html` — the HTML of the commented element (use this to locate the source component)
   - `element_selector` — CSS selector of the element
   - `page_url` — which page the comment is on
3. **Locate source code**: Use `element_html` and `element_selector` to find the corresponding source file and component. The code was recently generated, so the structure is familiar.
4. **Make changes**: Implement the requested fix for each comment
5. **Resolve**: After fixing a comment, call `awr_resolve_comment(comment_id="<id>")` to mark it done. The browser extension will update in real-time via SSE.
