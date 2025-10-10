FROM python:3.10-bullseye

# Install ClamAV dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        clamav \
        clamav-daemon \
        netcat \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy your app
COPY app.py /app/

# Run the application
CMD ["python", "app.py"]
