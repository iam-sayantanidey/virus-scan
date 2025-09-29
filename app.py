import boto3
import os
import tempfile
import subprocess
from urllib.parse import unquote_plus

# Initialize S3 client
s3 = boto3.client('s3')

# Load environment variables
UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET")
CLEAN_BUCKET = os.environ.get("CLEAN_BUCKET")
QUARANTINE_BUCKET = os.environ.get("QUARANTINE_BUCKET")

# Validate environment variables
if not UPLOAD_BUCKET or not CLEAN_BUCKET or not QUARANTINE_BUCKET:
    raise ValueError(
        "Environment variables UPLOAD_BUCKET, CLEAN_BUCKET, QUARANTINE_BUCKET must be set"
    )

# Maximum seconds to allow clamscan to run
CLAMSCAN_TIMEOUT = 90  # Adjust based on Lambda timeout

def scan_file(file_path):
    """
    Scan the file using clamscan CLI.
    Returns True if clean, False if infected or timed out.
    """
    print(f"Starting ClamAV scan for {file_path}...")
    try:
        result = subprocess.run(
            ["clamscan", "--no-summary", file_path],
            capture_output=True,
            text=True,
            timeout=CLAMSCAN_TIMEOUT
        )
        print("ClamAV output:", result.stdout)
        print(f"ClamAV return code: {result.returncode}")
        if result.returncode == 0:
            return True
        elif result.returncode == 1:
            print(f"Virus detected in file {file_path}")
            return False
        else:
            print(f"ClamAV error scanning file {file_path}")
            return False
    except subprocess.TimeoutExpired:
        print(f"ClamAV scan timed out for {file_path}")
        return False
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
        return False

def lambda_handler(event, context):
    for record in event.get('Records', []):
        bucket_name = record['s3']['bucket']['name']
        object_key = unquote_plus(record['s3']['object']['key'])
        print(f"Processing file: {object_key} from bucket: {bucket_name}")

        # Download file to /tmp
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(object_key)[1]) as tmp_file:
            try:
                print(f"Downloading file {object_key} from bucket {bucket_name}...")
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
                print(f"Uploading file to {dest_bucket}/{object_key}...")
                s3.upload_file(tmp_file.name, dest_bucket, object_key)
                print(f"File uploaded successfully to {dest_bucket}/{object_key}")

                s3.delete_object(Bucket=bucket_name, Key=object_key)
                print(f"Deleted original file {object_key} from bucket {bucket_name}")
                
            except Exception as e:
                print(f"Error uploading/deleting file {object_key}: {e}")
