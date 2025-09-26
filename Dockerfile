# Use AWS Lambda Python 3.10 base image
FROM public.ecr.aws/lambda/python:3.10

# Install ClamAV and required tools
RUN yum -y install clamav clamav-update
RUN freshclam

# Copy Lambda function code and dependencies
COPY app.py requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set the Lambda entry point
CMD ["app.lambda_handler"]
