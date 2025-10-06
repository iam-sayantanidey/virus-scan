FROM python:3.10-slim

# Install ClamAV and Python dependencies
RUN apt-get update && \
    apt-get install -y clamav clamav-daemon && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app and entrypoint script
COPY app.py entrypoint.sh .

# Make sure the entrypoint is executable
RUN chmod +x entrypoint.sh

# Expose ClamAV port (optional)
EXPOSE 3310

# Use entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
