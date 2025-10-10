FROM python:3.10-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    clamav \
    clamav-freshclam \
    && rm -rf /var/lib/apt/lists/*

# Prepare ClamAV database directory
RUN mkdir -p /var/lib/clamav && chown -R clamav:clamav /var/lib/clamav

WORKDIR /app
COPY app.py requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Update virus definitions at startup, then run the poller
CMD freshclam && python3 app.py
