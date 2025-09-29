# Use AWS Lambda Python 3.10 base image
FROM public.ecr.aws/lambda/python:3.10

# Install ClamAV and required tools
RUN yum -y install clamav clamav-update clamd && yum clean all

# Update ClamAV virus database
RUN freshclam

# Create ClamAV runtime directory
RUN mkdir -p /var/run/clamd && chown -R root:root /var/run/clamd

# Copy your Lambda code into the container
COPY app.py ${LAMBDA_TASK_ROOT}

# Install Python dependencies (clamd, boto3, etc.)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Expose the ClamAV UNIX socket directory (optional but good practice)
ENV CLAMD_SOCKET=/var/run/clamd/clamd.sock

# Start clamd in background and then run Lambda
CMD [ "sh", "-c", "clamd & python -m awslambdaric app.lambda_handler" ]

