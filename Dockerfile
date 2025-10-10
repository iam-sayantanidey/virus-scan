FROM python:3.10-slim

# Install system dependencies required for ClamAV
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        clamav \
        clamav-daemon \
        netcat \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy your application code
COPY app.py /app/

# (Optional) Install Python dependencies if you have a requirements.txt
# COPY requirements.txt /app/
# RUN pip install --no-cache-dir -r requirements.txt

# Run the application
CMD ["python", "app.py"]
