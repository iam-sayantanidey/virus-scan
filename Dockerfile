FROM python:3.10-slim

# Install dependencies and ClamAV
RUN apt-get update && apt-get install -y \
    clamav \
    clamav-daemon \
    clamav-freshclam \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories and set permissions
RUN mkdir -p /var/run/clamav /var/lib/clamav \
    && chown -R clamav:clamav /var/run/clamav /var/lib/clamav \
    && chmod 755 /var/run/clamav

# Update virus definitions during build (optional but helps first start)
RUN freshclam || true

# Set working directory
WORKDIR /app

# Copy Python code and requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY entrypoint.sh ./

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh

# Expose clamd default port (optional)
EXPOSE 3310

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
