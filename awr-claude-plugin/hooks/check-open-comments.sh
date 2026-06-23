#!/usr/bin/env bash
# AWR Stop hook: check for open web-review comments before the turn ends.
#
# Behavior:
#   - queries the local AWR server for open comments
#   - if the server is offline / unreachable / errors: exit 0 silently (don't disturb)
#   - if there are N > 0 open comments: emit a systemMessage so the user is prompted
#     to run /awr (non-blocking — Claude still stops normally; the message is shown
#     to the user, not fed back to Claude, so there is no block loop)
#   - if N == 0: print nothing, exit 0
#
# Why systemMessage (not decision:block / additionalContext):
#   Both block and additionalContext make the conversation continue so Claude can act
#   on them, which would re-trigger Stop and risk a loop (the 8-consecutive-block cap
#   eventually breaks it, but it's noisy and not what we want). systemMessage is shown
#   to the user only and lets Claude stop cleanly, leaving the decision to run /awr
#   with the user — matching issue #5's acceptance.
#
# Wired up by hooks/hooks.json.

set -u

AWR_URL="http://localhost:9876/api/comments?status=open"

# Fetch open comments. --max-time bounds the whole request so an offline server
# can't stall the Stop event. On any failure (timeout, connection refused, non-2xx,
# or non-JSON body) we bail out silently.
response=$(curl -s --max-time 2 -w '\n%{http_code}' "$AWR_URL" 2>/dev/null) || exit 0

# Split body and status code.
http_code=$(printf '%s' "$response" | tail -n1)
body=$(printf '%s' "$response" | sed '$d')

case "$http_code" in
  2*) ;;  # success, continue
  *) exit 0 ;;  # offline or error -> silent
esac

# Count array elements. jq is the robust path; fall back silently if absent.
if command -v jq >/dev/null 2>&1; then
  # Treat non-array (or invalid) JSON as offline -> silent.
  n=$(printf '%s' "$body" | jq 'if type == "array" then length else -1 end' 2>/dev/null) || exit 0
  [ "$n" = "-1" ] && exit 0
else
  # Best-effort fallback: count top-level object boundaries. Good enough for a hint.
  n=$(printf '%s' "$body" | grep -o '"id"' | wc -l | tr -d ' ')
fi

if [ "${n:-0}" -gt 0 ] 2>/dev/null; then
  # systemMessage is shown to the user (not to Claude), non-blocking, no loop risk.
  printf '{"systemMessage":"⏳ AWR: %s 条未处理的 web 评论待处理，可运行 /awr 处理。"}\n' "$n"
fi

exit 0
