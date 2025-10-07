#!/bin/bash
set -e

echo "[INFO] Preparing ClamAV directories..."
mkdir -p /var/run/clamav /var/lib/clamav
chown -R clamav:clamav /var/run/clamav /var/lib/clamav
chmod 755 /var/run/clamav

echo "[INFO] Updating ClamAV virus definitions..."
freshclam || echo "[WARN] freshclam failed, continuing with existing DB."

echo "[INFO] Starting ClamAV daemon..."
clamd &

# Wait for clamd to start
echo "[INFO] Waiting for ClamAV to be ready..."
for i in {1..30}; do
    if nc -z localhost 3310; then
        echo "[INFO] ✅ ClamAV daemon is up and running!"
        break
    fi
    echo "[INFO] Waiting for clamd... ($i/30)"
    sleep 2
done

if ! nc -z localhost 3310; then
    echo "[ERROR] ❌ ClamAV daemon did not start properly!"
    exit 1
fi

echo "[INFO] 🚀 Starting virus scanning service..."
exec python /app/app.py
