import boto3
import os
import json
import tempfile
import subprocess
import logging
import time
from urllib.parse import unquote_plus

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger()

# AWS clients
s3 = boto3.client("s3")
sqs = boto3.client("sqs")

UPLOAD_BUCKET = os.environ["UPLOAD_BUCKET"]
CLEAN_BUCKET = os.environ["CLEAN_BUCKET"]
QUARANTINE_BUCKET = os.environ["QUARANTINE_BUCKET"]
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]

CLAMSCAN_TIMEOUT = 90  # seconds

def update_virus_definitions():
    """Update ClamAV definitions with retries."""
    retries = 3
    for i in range(retries):
        try:
            log.info("Updating ClamAV virus definitions...")
            subprocess.run(["freshclam", "--quiet"], check=True, timeout=60)
            log.info("Virus definitions updated successfully.")
            return
        except subprocess.TimeoutExpired:
            log.warning(f"Freshclam attempt {i+1} timed out, retrying...")
        except Exception as e:
            log.warning(f"Freshclam attempt {i+1} failed: {e}")
        time.sleep(5)
    log.error("Failed to update virus definitions after 3 attempts. Scanning may be inaccurate.")

def scan_file(file_path):
    try:
        result = subprocess.run(
            ["clamscan", "--no-summary", file_path],
            capture_output=True,
            text=True,
            timeout=CLAMSCAN_TIMEOUT
        )
        log.info(f"ClamAV output: {result.stdout.strip()}")
        return result.returncode == 0  # 0 = clean, 1 = infected
    except Exception as e:
        log.error(f"Error scanning {file_path}: {e}")
        return False

def process_message(message_body):
    record = json.loads(message_body)["Records"][0]
    bucket_name = record["s3"]["bucket"]["name"]
    object_key = unquote_plus(record["s3"]["object"]["key"])
    log.info(f"Processing {object_key} from {bucket_name}")

    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(object_key)[1]) as tmp_file:
        s3.download_file(bucket_name, object_key, tmp_file.name)
        log.info(f"Downloaded {object_key} to {tmp_file.name}")

        is_clean = scan_file(tmp_file.name)
        dest_bucket = CLEAN_BUCKET if is_clean else QUARANTINE_BUCKET

        s3.upload_file(tmp_file.name, dest_bucket, object_key)
        log.info(f"Uploaded to {dest_bucket}/{object_key}")

        s3.delete_object(Bucket=bucket_name, Key=object_key)
        log.info(f"Deleted {object_key} from {bucket_name}")

def main():
    update_virus_definitions()  # Run at startup
    log.info("Starting SQS poller...")
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10
            )
            messages = response.get("Messages", [])
            if not messages:
                log.info("No messages in queue. Waiting...")
                continue

            for msg in messages:
                try:
                    process_message(msg["Body"])
                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=msg["ReceiptHandle"]
                    )
                    log.info("Message deleted from SQS")
                except Exception as e:
                    log.error(f"Error processing message: {e}")
        except Exception as e:
            log.error(f"SQS polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
