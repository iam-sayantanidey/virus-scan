#!/bin/bash
set -e

echo "[INFO] Preparing ClamAV environment..."
mkdir -p /var/run/clamav
chown clamav:clamav /var/run/clamav
chmod 755 /var/run/clamav

echo "[INFO] Updating virus definitions..."
freshclam || echo "[WARN] freshclam failed, continuing with existing DB..."

echo "[INFO] Starting ClamAV daemon..."
clamd &

# Wait until clamd is ready
echo "[INFO] Waiting for ClamAV to start..."
sleep 8

# Health check (optional)
if ! nc -z localhost 3310; then
  echo "[ERROR] ClamAV daemon did not start properly!"
  exit 1
fi

echo "[INFO] Starting Python scanner..."
exec python /app/app.py
