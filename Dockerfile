# Use official Python base image (not Lambda base anymore)
FROM python:3.10-slim

# Install system dependencies and ClamAV
RUN apt-get update && apt-get install -y \
    clamav \
    clamav-daemon \
    clamav-freshclam \
    && rm -rf /var/lib/apt/lists/*

# Update ClamAV virus definitions at build time
RUN freshclam

# Set work directory
WORKDIR /app

# Copy application code
COPY app.py /app/

# Copy and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Optional: add a healthcheck for ECS (can skip if not needed)
HEALTHCHECK CMD clamscan --version || exit 1

# Default command: run the script
CMD ["python3", "app.py"]

