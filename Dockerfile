FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    clamav \
    clamav-daemon \
    netcat \
    && rm -rf /var/lib/apt/lists/*

# Update ClamAV virus definitions at build time
RUN freshclam

# Set working directory
WORKDIR /app

# Copy your app
COPY app.py /app/

# Install Python dependencies if needed
# COPY requirements.txt /app/
# RUN pip install --no-cache-dir -r requirements.txt

# Run your app directly
CMD ["python", "app.py"]
