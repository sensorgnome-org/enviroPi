#!/usr/bin/env python3
import os
import time
import logging
from datetime import date, datetime
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from enpi import __version__,__log_dir__,__data_dir__,__sitename_file__

DATA_DIR = __data_dir__
SECRETS_FILE = "/opt/enpi/secrets.env"
UPLOADED_LOG = "/opt/enpi/uploaded.log"
LOG_FILE = f"{__log_dir__}/uploader.log"
with open(__sitename_file__, "r") as f:
    SITE_NAME = f.read().strip()

def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s %(message)s"
    )

def load_secrets(path):
    secrets = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            secrets[key.strip()] = value.strip()
    return secrets

def load_uploaded_set():
    if not os.path.exists(UPLOADED_LOG):
        return set()
    with open(UPLOADED_LOG) as f:
        return {line.strip() for line in f if line.strip()}

def mark_uploaded(filename):
    with open(UPLOADED_LOG, "a") as f:
        f.write(filename + "\n")

def is_completed_daily_csv(filename):
    # Expect format: something_YYYY-MM-DD.csv
    try:
        date_str = filename.split("_")[-1].replace(".csv", "")
        file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        return file_date < date.today()
    except Exception:
        return False

def upload_file(s3, bucket, filepath):
    filename = os.path.basename(filepath)
    s3_key = SITE_NAME + "/" + filename.replace("@", "/")

    logging.info(f"Uploading {filename} → s3://{bucket}/{s3_key}")

    try:
        s3.upload_file(filepath, bucket, s3_key)
        logging.info(f"Upload succeeded for {filename}")
        return True
    except (BotoCoreError, ClientError) as e:
        logging.error(f"Upload failed for {filename}: {e}")
        return False

def main():
    setup_logging()
    logging.info("Uploader started")

    if not os.path.isdir(DATA_DIR):
        logging.error(f"Data directory missing: {DATA_DIR}")
        return

    if not os.path.isfile(SECRETS_FILE):
        logging.error(f"Secrets file missing: {SECRETS_FILE}")
        return

    secrets = load_secrets(SECRETS_FILE)
    bucket = secrets.get("BUCKET_NAME") 
    aws_id = secrets.get("AWS_ACCESS_KEY_ID")
    aws_key = secrets.get("AWS_SECRET_ACCESS_KEY")

    if not bucket or not aws_id or not aws_key:
        logging.error("Missing required AWS credentials in secrets file")
        return

    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_id,
        aws_secret_access_key=aws_key
    )

    uploaded = load_uploaded_set()

    while True:
        files = sorted(os.listdir(DATA_DIR))
        for f in files:
            if not f.endswith(".csv"):
                continue
            if f.startswith("_"):
                continue
            if not is_completed_daily_csv(f):
                continue
            if f in uploaded:
                continue

            full_path = os.path.join(DATA_DIR, f)
            if upload_file(s3, bucket, full_path):
                mark_uploaded(f)
                # Optional: delete after upload
                # os.remove(full_path)

        time.sleep(30)

if __name__ == "__main__":
    main()