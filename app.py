import boto3
import os
import time
import tempfile
import clamd
from urllib.parse import unquote_plus
from botocore.exceptions import ClientError

# AWS clients
s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# Environment variables
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
CLEAN_BUCKET = os.environ["CLEAN_BUCKET"]
QUARANTINE_BUCKET = os.environ["QUARANTINE_BUCKET"]

# Initialize ClamAV daemon with retry
def init_clamd(retries=5, delay=5):
    for i in range(retries):
        try:
            cd = clamd.ClamdNetworkSocket(host='localhost', port=3310)
            cd.ping()
            print("[INFO] Connected to ClamAV daemon.")
            return cd
        except Exception as e:
            print(f"[WARN] ClamAV not ready (attempt {i+1}/{retries}): {e}")
            time.sleep(delay)
    raise Exception("Failed to connect to ClamAV daemon.")

cd = init_clamd()

def process_message(message):
    try:
        body = message["Body"]
        record = eval(body)["Records"][0]
        bucket_name = record["s3"]["bucket"]["name"]
        object_key = unquote_plus(record["s3"]["object"]["key"])

        print(f"[INFO] Processing file: s3://{bucket_name}/{object_key}")

        with tempfile.NamedTemporaryFile() as tmp_file:
            s3.download_file(bucket_name, object_key, tmp_file.name)

            scan_result = cd.scan(tmp_file.name)
            print(f"[INFO] Scan result: {scan_result}")

            if scan_result[tmp_file.name][0] == "OK":
                s3.upload_file(tmp_file.name, CLEAN_BUCKET, object_key)
                print(f"[SUCCESS] Clean file uploaded: s3://{CLEAN_BUCKET}/{object_key}")
            else:
                s3.upload_file(tmp_file.name, QUARANTINE_BUCKET, object_key)
                print(f"[ALERT] Infected file moved: s3://{QUARANTINE_BUCKET}/{object_key}")

        sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=message["ReceiptHandle"])
        print("[INFO] Message deleted from SQS.")

    except Exception as e:
        print(f"[ERROR] Failed to process message: {e}")

def poll_sqs():
    print("[INFO] Virus scan service started. Polling SQS...")
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
            )

            messages = response.get("Messages", [])
            if not messages:
                print("[INFO] No messages. Sleeping 10s...")
                time.sleep(10)
                continue

            print(f"[INFO] Received {len(messages)} messages. Processing...")
            for message in messages:
                process_message(message)

        except ClientError as e:
            print(f"[AWS ERROR] {e}")
            time.sleep(15)
        except Exception as e:
            print(f"[FATAL ERROR] {e}")
            time.sleep(15)

if __name__ == "__main__":
    poll_sqs()
