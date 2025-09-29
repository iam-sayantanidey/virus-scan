import boto3
import os
import tempfile
import subprocess
from urllib.parse import unquote_plus

# Initialize S3 client
s3 = boto3.client('s3')

# Buckets
UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET")         # e.g., 'upload-bucket-virus-scan'
CLEAN_BUCKET = os.environ.get("CLEAN_BUCKET")           # e.g., 'clean-bucket-virus-scan'
QUARANTINE_BUCKET = os.environ.get("QUARANTINE_BUCKET") # e.g., 'quarantine-bucket-virus-scan'

def scan_file(file_path):
    """
    Scan the file using clamscan CLI
    Returns True if clean, False if infected
    """
    try:
        result = subprocess.run(["clamscan", file_path], capture_output=True, text=True)
        print("ClamAV output:", result.stdout)
        # clamscan returns 0 if no virus, 1 if virus found
        return result.returncode == 0
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
        return False

def lambda_handler(event, context):
    for record in event.get('Records', []):
        bucket_name = record['s3']['bucket']['name']
        object_key = unquote_plus(record['s3']['object']['key'])
        print(f"Processing file: {object_key} from bucket: {bucket_name}")

        # Download file to /tmp
        with tempfile.NamedTemporaryFile() as tmp_file:
            try:
                s3.download_file(bucket_name, object_key, tmp_file.name)
                print(f"File downloaded to {tmp_file.name}")
            except Exception as e:
                print(f"Error downloading file {object_key}: {e}")
                continue

            # Scan the file
            is_clean = scan_file(tmp_file.name)

            # Decide destination bucket
            dest_bucket = CLEAN_BUCKET if is_clean else QUARANTINE_BUCKET

            # Upload the file
            try:
                s3.upload_file(tmp_file.name, dest_bucket, object_key)
                print(f"File uploaded to {dest_bucket}/{object_key}")
            except Exception as e:
                print(f"Error uploading file {object_key} to {dest_bucket}: {e}")
