# Use reliable Debian-based Python image
FROM python:3.10-bullseye

# Install ClamAV and netcat
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        clamav \
        clamav-daemon \
        netcat \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application code and Python dependencies
COPY app.py /app/
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the application
CMD ["python", "app.py"]
