import boto3
import os
import time
import tempfile
import clamd
from urllib.parse import unquote_plus
from botocore.exceptions import ClientError

# Initialize AWS clients
s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# Environment variables
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
CLEAN_BUCKET = os.environ["CLEAN_BUCKET"]
QUARANTINE_BUCKET = os.environ["QUARANTINE_BUCKET"]

# Initialize ClamAV daemon
cd = clamd.ClamdNetworkSocket(host='localhost', port=3310)

def process_message(message):
    """
    Process a single SQS message: download S3 object, scan it, and move to clean or quarantine bucket.
    """
    try:
        body = message["Body"]
        record = eval(body)["Records"][0]  # Convert string back to dict
        bucket_name = record["s3"]["bucket"]["name"]
        object_key = unquote_plus(record["s3"]["object"]["key"])

        print(f"[INFO] Processing file: s3://{bucket_name}/{object_key}")

        # Download file to a temp location
        with tempfile.NamedTemporaryFile() as tmp_file:
            s3.download_file(bucket_name, object_key, tmp_file.name)

            # Scan the file
            scan_result = cd.scan(tmp_file.name)
            print(f"[INFO] Scan result: {scan_result}")

            if scan_result[tmp_file.name][0] == "OK":
                # File is clean → upload to clean bucket
                s3.upload_file(tmp_file.name, CLEAN_BUCKET, object_key)
                print(f"[SUCCESS] Clean file uploaded to: s3://{CLEAN_BUCKET}/{object_key}")
            else:
                # File is infected → upload to quarantine bucket
                s3.upload_file(tmp_file.name, QUARANTINE_BUCKET, object_key)
                print(f"[ALERT] Infected file moved to: s3://{QUARANTINE_BUCKET}/{object_key}")

        # Delete message from SQS after processing
        sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=message["ReceiptHandle"])
        print("[INFO] Message deleted from SQS queue.")

    except Exception as e:
        print(f"[ERROR] Failed to process message: {e}")


def poll_sqs():
    """
    Continuously poll the SQS queue for new messages.
    """
    print("[INFO] Virus scan service started. Polling SQS for messages...")

    while True:
        try:
            # Poll up to 10 messages at a time
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,  # Enable long polling (reduces empty responses)
            )

            messages = response.get("Messages", [])

            if not messages:
                print("[INFO] No messages found. Sleeping for 10 seconds...")
                time.sleep(10)
                continue

            print(f"[INFO] Received {len(messages)} messages. Processing...")
            for message in messages:
                process_message(message)

        except ClientError as e:
            print(f"[AWS ERROR] {e}")
            time.sleep(15)
        except Exception as e:
            print(f"[FATAL ERROR] Unexpected error: {e}")
            time.sleep(15)


if __name__ == "__main__":
    poll_sqs()
