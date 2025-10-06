# Base image
FROM python:3.10-slim

# Install ClamAV and dependencies
RUN apt-get update && \
    apt-get install -y clamav clamav-daemon && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code and entrypoint
COPY app.py entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose ClamAV port (optional)
EXPOSE 3310

# Entrypoint
ENTRYPOINT ["./entrypoint.sh"]
