import os
import time
import boto3
import clamd
import tempfile
import logging
from urllib.parse import unquote_plus
from botocore.exceptions import ClientError

# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger()

# ----------------------------
# Environment Variables
# ----------------------------
UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET")
CLEAN_BUCKET = os.environ.get("CLEAN_BUCKET")
QUARANTINE_BUCKET = os.environ.get("QUARANTINE_BUCKET")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")

if not all([UPLOAD_BUCKET, CLEAN_BUCKET, QUARANTINE_BUCKET, SQS_QUEUE_URL]):
    logger.error("❌ Missing required environment variables.")
    exit(1)

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# ----------------------------
# Connect to ClamAV
# ----------------------------
def connect_to_clamd(retries=10, delay=5):
    for i in range(retries):
        try:
            logger.info(f"🔍 Connecting to ClamAV daemon (attempt {i+1}/{retries})...")
            cd = clamd.ClamdNetworkSocket(host="localhost", port=3310)
            cd.ping()
            logger.info("✅ Connected to ClamAV.")
            return cd
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to ClamAV: {e}")
            time.sleep(delay)
    logger.error("❌ Failed to connect to ClamAV.")
    exit(1)

cd = connect_to_clamd()

# ----------------------------
# File Scan Logic
# ----------------------------
def scan_file(path):
    try:
        result = cd.scan(path)
        logger.info(f"🦠 Scan result: {result}")
        if result is None:
            return "ERROR"
        status = list(result.values())[0][0]
        return status
    except Exception as e:
        logger.error(f"❌ Error scanning file: {e}")
        return "ERROR"

def process_message(msg):
    try:
        body = eval(msg["Body"])
        record = body["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        logger.info(f"📥 Processing file: s3://{bucket}/{key}")

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            s3.download_fileobj(bucket, key, tmp_file)
            tmp_path = tmp_file.name

        result = scan_file(tmp_path)

        if result == "OK":
            logger.info("✅ Clean file. Uploading to clean bucket...")
            s3.upload_file(tmp_path, CLEAN_BUCKET, key)
        else:
            logger.warning("🚨 Infected or scan failed. Uploading to quarantine bucket...")
            s3.upload_file(tmp_path, QUARANTINE_BUCKET, key)

        os.remove(tmp_path)
        logger.info("🧹 Temporary file removed.")

    except Exception as e:
        logger.error(f"❌ Failed to process message: {e}")

# ----------------------------
# Poll SQS Forever
# ----------------------------
logger.info("🚀 Virus scanning service started. Polling SQS...")
while True:
    try:
        resp = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
        messages = resp.get("Messages", [])
        if not messages:
            logger.info("📭 No messages. Waiting...")
            continue

        for msg in messages:
            process_message(msg)
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=msg["ReceiptHandle"]
            )
            logger.info("✅ Message processed and deleted.")

    except ClientError as e:
        logger.error(f"❌ AWS ClientError: {e}")
        time.sleep(5)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        time.sleep(5)
