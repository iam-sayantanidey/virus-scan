import os
import time
import boto3
import clamd
import tempfile
import logging
from urllib.parse import unquote_plus
from botocore.exceptions import ClientError

# ----------------------------
# Logging setup
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger()

# ----------------------------
# Environment variables
# ----------------------------
UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET")
CLEAN_BUCKET = os.environ.get("CLEAN_BUCKET")
QUARANTINE_BUCKET = os.environ.get("QUARANTINE_BUCKET")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")

if not all([UPLOAD_BUCKET, CLEAN_BUCKET, QUARANTINE_BUCKET, SQS_QUEUE_URL]):
    logger.error("❌ One or more required environment variables are missing.")
    exit(1)

# ----------------------------
# AWS Clients
# ----------------------------
s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# ----------------------------
# ClamAV client
# ----------------------------
def connect_to_clamd(retries=5, delay=5):
    for i in range(retries):
        try:
            logger.info("🔍 Connecting to ClamAV daemon (attempt %d/%d)...", i+1, retries)
            cd = clamd.ClamdNetworkSocket(host='localhost', port=3310)
            cd.ping()
            logger.info("✅ Connected to ClamAV daemon.")
            return cd
        except Exception as e:
            logger.warning("⚠️ Could not connect to ClamAV: %s", str(e))
            time.sleep(delay)
    logger.error("❌ Failed to connect to ClamAV after %d attempts.", retries)
    exit(1)

cd = connect_to_clamd()

# ----------------------------
# File scanning function
# ----------------------------
def scan_file(local_path):
    try:
        result = cd.scan(local_path)
        logger.info("🦠 Scan result: %s", result)
        if result is None:
            return "ERROR"

        status = list(result.values())[0][0]
        return status
    except Exception as e:
        logger.error("❌ Error scanning file: %s", str(e))
        return "ERROR"

# ----------------------------
# Process SQS message
# ----------------------------
def process_message(message):
    try:
        body = message['Body']
        record = eval(body) if isinstance(body, str) else body  # Adjust if S3 event format
        s3_event = record['Records'][0]['s3']
        bucket = s3_event['bucket']['name']
        key = unquote_plus(s3_event['object']['key'])

        logger.info(f"📥 New file to scan: s3://{bucket}/{key}")

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            s3.download_fileobj(bucket, key, tmp_file)
            tmp_file_path = tmp_file.name

        result = scan_file(tmp_file_path)

        if result == "OK":
            logger.info("✅ File is clean. Uploading to clean bucket...")
            s3.upload_file(tmp_file_path, CLEAN_BUCKET, key)
        else:
            logger.warning("🚨 File is INFECTED or scan failed. Uploading to quarantine bucket...")
            s3.upload_file(tmp_file_path, QUARANTINE_BUCKET, key)

        os.remove(tmp_file_path)
        logger.info("🧹 Temporary file removed.")

    except Exception as e:
        logger.error("❌ Failed to process message: %s", str(e))

# ----------------------------
# Main SQS Polling Loop
# ----------------------------
logger.info("🚀 Virus scanner started. Listening for messages on SQS queue...")
while True:
    try:
        response = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,
        )

        messages = response.get('Messages', [])
        if not messages:
            logger.info("📭 No messages in queue. Waiting...")
            continue

        for message in messages:
            process_message(message)
            # Delete message after processing
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )
            logger.info("✅ Message processed and deleted from queue.")

    except ClientError as e:
        logger.error("❌ AWS Client error: %s", e)
        time.sleep(5)
    except Exception as e:
        logger.error("❌ Unexpected error: %s", e)
        time.sleep(5)
