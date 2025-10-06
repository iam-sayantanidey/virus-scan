#!/bin/bash

# Update virus database
echo "[INFO] Updating ClamAV database..."
freshclam

# Start ClamAV daemon in background
echo "[INFO] Starting ClamAV daemon..."
clamd &

# Wait a few seconds for clamd to start
sleep 5

# Start Python app
echo "[INFO] Starting virus scan service..."
python app.py
