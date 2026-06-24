#!/bin/bash
# scripts/deploy.sh — Deploy AWR to piggy server
set -euo pipefail

PIGGY="xuchao@10.138.74.9"
REMOTE_DIR="/home/xuchao/agent-web-review"

echo ">>> Syncing server code..."
rsync -avz --delete \
  --exclude='server/data/' \
  --exclude='server/venv/' \
  --exclude='server/.venv/' \
  --exclude='server/__pycache__/' \
  --exclude='server/app/__pycache__/' \
  --exclude='server/app/*/__pycache__/' \
  --exclude='.git/' \
  ./server/ ${PIGGY}:${REMOTE_DIR}/server/

echo ">>> Syncing extension code..."
rsync -avz --delete \
  --exclude='.git/' \
  ./extension/ ${PIGGY}:${REMOTE_DIR}/extension/

echo ">>> Installing dependencies & restarting..."
ssh ${PIGGY} << 'EOF'
cd ~/agent-web-review/server
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q
if systemctl is-active --quiet awr; then
  sudo systemctl restart awr
  echo ">>> Service restarted"
else
  echo ">>> Service not running. Start manually: sudo systemctl start awr"
fi
EOF

echo ">>> Health check..."
sleep 2
if ssh ${PIGGY} "curl -sf http://localhost:9876/api/health" > /dev/null 2>&1; then
  echo ">>> Deployed successfully — service is healthy"
else
  echo ">>> WARNING: Health check failed. Check service status."
fi
