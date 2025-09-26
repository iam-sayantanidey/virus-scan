import boto3
import os
import tempfile
import clamd
from urllib.parse import unquote_plus

# Initialize S3 client
s3 = boto3.client('s3')

# Hardcode bucket names
UPLOAD_BUCKET = 'upload-bucket-virus-scan'
CLEAN_BUCKET = 'clean-bucket-virus-scan'
QUARANTINE_BUCKET = 'quarantine-bucket-virus-scan'

# Initialize ClamAV daemon
cd = clamd.ClamdUnixSocket()  # Uses local clamd socket inside container

def lambda_handler(event, context):
    """
    Lambda entry point for S3-triggered virus scan
    """
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        object_key = unquote_plus(record['s3']['object']['key'])
        print(f"Processing file: s3://{bucket_name}/{object_key}")

        # Create temporary file
        with tempfile.NamedTemporaryFile() as tmp_file:
            # Download file from S3
            s3.download_file(bucket_name, object_key, tmp_file.name)

            try:
                # Scan file with ClamAV
                result = cd.scan(tmp_file.name)
                print(f"Scan result: {result}")

                # Check if infected
                if result[tmp_file.name][0] == 'OK':
                    # Upload to clean bucket
                    s3.upload_file(tmp_file.name, CLEAN_BUCKET, object_key)
                    print(f"File is clean. Uploaded to {CLEAN_BUCKET}/{object_key}")
                else:
                    # Upload to quarantine bucket
                    s3.upload_file(tmp_file.name, QUARANTINE_BUCKET, object_key)
                    print(f"File is infected. Uploaded to {QUARANTINE_BUCKET}/{object_key}")

            except Exception as e:
                print(f"Error scanning file {object_key}: {str(e)}")
