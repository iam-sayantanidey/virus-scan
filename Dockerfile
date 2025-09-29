# Use AWS Lambda Python 3.10 base image
FROM public.ecr.aws/lambda/python:3.10

# Install ClamAV CLI and required tools
RUN yum -y install clamav clamav-update && yum clean all

# Update ClamAV virus database at build time
RUN freshclam

# Copy your Lambda code
COPY app.py ${LAMBDA_TASK_ROOT}/

# Copy Python dependencies and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Command for Lambda to start
CMD ["app.lambda_handler"]
