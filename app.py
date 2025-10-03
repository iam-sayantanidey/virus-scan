import boto3
import os
import json
import tempfile
import subprocess
from urllib.parse import unquote_plus

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

UPLOAD_BUCKET = os.environ["UPLOAD_BUCKET"]
CLEAN_BUCKET = os.environ["CLEAN_BUCKET"]
QUARANTINE_BUCKET = os.environ["QUARANTINE_BUCKET"]
SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]

CLAMSCAN_TIMEOUT = 90  # seconds

def scan_file(file_path):
    try:
        result = subprocess.run(
            ["clamscan", "--no-summary", file_path],
            capture_output=True,
            text=True,
            timeout=CLAMSCAN_TIMEOUT
        )
        print("ClamAV output:", result.stdout)
        return result.returncode == 0  # 0=clean, 1=infected
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")
        return False

def process_message(message_body):
    record = json.loads(message_body)["Records"][0]
    bucket_name = record["s3"]["bucket"]["name"]
    object_key = unquote_plus(record["s3"]["object"]["key"])
    print(f"Processing {object_key} from {bucket_name}")

    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(object_key)[1]) as tmp_file:
        s3.download_file(bucket_name, object_key, tmp_file.name)
        print(f"Downloaded to {tmp_file.name}")

        is_clean = scan_file(tmp_file.name)
        dest_bucket = CLEAN_BUCKET if is_clean else QUARANTINE_BUCKET

        s3.upload_file(tmp_file.name, dest_bucket, object_key)
        print(f"Uploaded to {dest_bucket}/{object_key}")

        s3.delete_object(Bucket=bucket_name, Key=object_key)
        print(f"Deleted {object_key} from {bucket_name}")

def main():
    response = sqs.receive_message(
        QueueUrl=SQS_QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5
    )

    messages = response.get("Messages", [])
    if not messages:
        print("No messages in queue, exiting.")
        return

    for msg in messages:
        try:
            process_message(msg["Body"])
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=msg["ReceiptHandle"]
            )
            print("Message deleted from SQS")
        except Exception as e:
            print(f"Error processing message: {e}")

if __name__ == "__main__":
    main()
