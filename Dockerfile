FROM python:3.10-slim

# Install dependencies for ClamAV
RUN apt-get update && \
    apt-get install -y clamav clamav-daemon && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app.py .

# Update ClamAV virus database
RUN freshclam

# Expose ClamAV port (optional, since using localhost)
EXPOSE 3310

# Run the app
CMD ["python", "app.py"]
