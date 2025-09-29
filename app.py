import boto3
import os
import tempfile
import clamd
from urllib.parse import unquote_plus

# Initialize S3 client
s3 = boto3.client('s3')

# Hardcoded bucket names
UPLOAD_BUCKET = 'upload-bucket-virus-scan'
CLEAN_BUCKET = 'clean-bucket-virus-scan'
QUARANTINE_BUCKET = 'quarantine-bucket-virus-scan'

# Initialize ClamAV daemon connection
print("🔍 Initializing ClamAV daemon connection...")
try:
    cd = clamd.ClamdUnixSocket()  # Uses local clamd socket inside container
    print("✅ Connected to clamd successfully:", cd.version())
except Exception as e:
    print(f"❌ Failed to connect to clamd: {e}")
    cd = None


def lambda_handler(event, context):
    """
    Lambda entry point for S3-triggered virus scan.
    Scans newly uploaded files and moves them to the clean or quarantine bucket.
    """

    print("🚀 Lambda triggered. Full event payload:")
    print(event)

    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        object_key = unquote_plus(record['s3']['object']['key'])

        print(f"📁 Processing file: s3://{bucket_name}/{object_key}")

        # Create a temporary file to download the object
        with tempfile.NamedTemporaryFile() as tmp_file:
            try:
                print("⬇️ Downloading file from S3...")
                s3.download_file(bucket_name, object_key, tmp_file.name)
                print("✅ File downloaded to temporary path:", tmp_file.name)
            except Exception as e:
                print(f"❌ Failed to download file {object_key} from S3: {e}")
                continue

            # Scan the file with ClamAV
            try:
                if not cd:
                    print("❌ Clamd connection was not initialized. Skipping scan.")
                    continue

                print("🦠 Starting virus scan...")
                result = cd.scan(tmp_file.name)
                print(f"🧪 Scan result: {result}")

                scan_status = result[tmp_file.name][0] if result else "UNKNOWN"

                if scan_status == 'OK':
                    print("✅ File is clean. Uploading to CLEAN bucket...")
                    s3.upload_file(tmp_file.name, CLEAN_BUCKET, object_key)
                    print(f"📤 Clean file uploaded to s3://{CLEAN_BUCKET}/{object_key}")

                else:
                    print("🚨 File is infected or scan failed. Uploading to QUARANTINE bucket...")
                    s3.upload_file(tmp_file.name, QUARANTINE_BUCKET, object_key)
                    print(f"📤 Infected file uploaded to s3://{QUARANTINE_BUCKET}/{object_key}")

            except Exception as e:
                print(f"❌ Error scanning or processing file {object_key}: {e}")

    print("✅ Lambda execution complete.")
    return {"status": "done"}
