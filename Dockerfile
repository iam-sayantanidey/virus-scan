FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    clamav \
    clamav-daemon \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# Create ClamAV directories and set permissions
RUN mkdir -p /var/run/clamav /var/lib/clamav && \
    chown -R clamav:clamav /var/run/clamav /var/lib/clamav && \
    chmod 755 /var/run/clamav

# Update virus database at build time (optional but recommended)
RUN freshclam || true

# Set working directory
WORKDIR /app

# Copy Python app and scripts
COPY app.py /app/
COPY requirements.txt /app/
COPY entrypoint.sh /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Expose clamd port (for health checks / debug)
EXPOSE 3310

# Default entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
