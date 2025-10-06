#!/bin/bash

# Update ClamAV virus database
freshclam

# Start ClamAV daemon in the background
clamd &

# Wait a few seconds for clamd to start
sleep 5

# Run the Python app
python app.py
