FROM python:3.10-slim

# Install system dependencies (using netcat-traditional)
RUN apt-get update -y \
 && apt-get install -y --no-install-recommends \
      clamav \
      clamav-daemon \
      netcat-traditional \
 && rm -rf /var/lib/apt/lists/*

# Create required directories with proper permissions
RUN mkdir -p /var/run/clamav /var/lib/clamav \
 && chown -R clamav:clamav /var/run/clamav /var/lib/clamav \
 && chmod 755 /var/run/clamav

# Update the virus database (ignore failures if mirrors are busy)
RUN freshclam || true

# Set working directory
WORKDIR /app

# Copy app code
COPY app.py requirements.txt entrypoint.sh /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Expose ClamAV port (optional)
EXPOSE 3310

# Start everything
ENTRYPOINT ["/app/entrypoint.sh"]
