FROM python:3.10-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y clamav clamav-daemon netcat && \
    rm -rf /var/lib/apt/lists/*

# Update ClamAV definitions
RUN freshclam

# Copy app
WORKDIR /app
COPY app.py .
COPY requirements.txt .

RUN pip install -r requirements.txt

# Expose port for clamd (default 3310)
EXPOSE 3310

# Start ClamAV daemon and then run your app
CMD service clamav-daemon start && \
    python3 app.py
