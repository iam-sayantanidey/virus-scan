FROM python:3.10-slim

# Install system dependencies required for ClamAV
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        clamav \
        clamav-daemon \
        netcat \
        gnupg \
        dirmngr \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Update ClamAV virus definitions at build time (quiet to avoid interactive prompts)
RUN freshclam --quiet

# Set working directory
WORKDIR /app

# Copy your app
COPY app.py /app/

# Install Python dependencies if needed
# COPY requirements.txt /app/
# RUN pip install --no-cache-dir -r requirements.txt

# Run your app directly
CMD ["python", "app.py"]
