#!/usr/bin/env python3
import os
import time
import json
import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import date, datetime
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from enpi import __version__,__log_dir__,__data_dir__,__sitename_file__
import urllib.request

with open(__sitename_file__, 'r') as f:
    station_info = json.load(f)
    SITE_NAME = station_info['station']


# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--data-dir", help="Data storage directory (default = /data)", type=str, default=__data_dir__)
parser.add_argument("-v", "--verbose", action="store_true", help="Log a lot of messages", default = False)
parser.add_argument("-ld", "--log-dir", help="Directory for logging data", type=str, default='/opt/sensorgnome/enpi/')
parser.add_argument("-s", "--secrets-file", help="Location of secrets file", type=str, default='/opt/sensorgnome/enpi/secrets.env')
parser.add_argument("-p", "--poll", action="store_true", help="Poll the AWS bucket to see if we can upload")
args = parser.parse_args()


DATA_DIR = args.data_dir
LOG_FILE = f"{__log_dir__}/uploader.log"

def setup_logging():
    handler = TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=14,   # keep 14 days of logs
        utc=False
    )
    formatter = logging.Formatter("(%(asctime)s) %(message)s")
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

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


def mark_uploaded(filename, filepath):
    uploaded_path = os.path.join(DATA_DIR, "uploaded_" + filename)
    os.rename(filepath, uploaded_path)


def is_completed_daily_csv(filename):
    # Expect format: something_YYYY-MM-DD.csv
    try:
        date_str = filename.split("_")[-1].replace(".csv", "").replace(".gz","")
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

def is_upload_candidate(f):
    return (
        f.endswith((".csv.gz",".csv"))
        and not f.startswith("uploaded_")
        and not f.startswith("_")
        and is_completed_daily_csv(f)
    )

def main():
    setup_logging()
    logging.info("Uploader started")

    if not os.path.isdir(DATA_DIR):
        print(json.dumps(["status", "no-data-dir"]), flush=True)
        logging.error(f"Data directory missing: {DATA_DIR}")
        return

    try:
        if args.secrets_file:
            secrets = load_secrets(args.secrets_file)
            bucket = secrets.get("BUCKET_NAME") 
            aws_id = secrets.get("AWS_ACCESS_KEY_ID")
            aws_key = secrets.get("AWS_SECRET_ACCESS_KEY")
        else:
            aws_id = os.environ.get("AWS_ACCESS_KEY_ID")
            aws_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
            bucket = os.environ.get("BUCKET_NAME")
    except Exception as e:
        print(json.dumps(["status", "no-secrets"]), flush=True)
        logging.error(f"Failed to load secrets: {e}")
        return

    if not bucket or not aws_id or not aws_key:
        print(json.dumps(["status", "no-secrets"]), flush=True)
        logging.error("Missing required AWS credentials in secrets file")
        return

    print(json.dumps(["data", {
        "bucket_name": bucket,
        "bucket_key": aws_id,
        "auth_key": "********"
    }]), flush=True)

    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_id,
        aws_secret_access_key=aws_key
    )
    
    bucket_exists = poll(s3, bucket)

    if args.poll: # We're done here
        return
    
    if not bucket_exists:
        print(json.dumps(["status", "no-s3-connection"]), flush=True)
        logging.error("Cannot reach S3, aborting upload")
        return
    
    files = [f for f in os.listdir(DATA_DIR) if is_upload_candidate(f)]

    if not files:
        logging.info("No files to upload")
        print(json.dumps(["status", "connected-no-files"]), flush=True)
        return
    


    for f in files:

        full_path = os.path.join(DATA_DIR, f)
        if upload_file(s3, bucket, full_path):
            mark_uploaded(f, full_path)
            # Optional: delete after upload
            # os.remove(full_path)

    print(json.dumps(["status", "done"]), flush=True)
    logging.info("Uploader finished")

def poll(s3, bucket):
    try:
        # head_bucket is the cheapest S3 call - just checks if bucket exists and is accessible
        s3.head_bucket(Bucket=bucket)
        print(json.dumps(["status", "connected"]), flush=True)
        logging.info("S3 bucket is accessible")
        
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '403':
            print(json.dumps(["status", "auth-error"]), flush=True)
            logging.error("S3 auth error - check credentials")
        elif error_code == '404':
            print(json.dumps(["status", "no-bucket"]), flush=True)
            logging.error(f"S3 bucket {bucket} not found")
        else:
            print(json.dumps(["status", "error"]), flush=True)
            logging.error(f"S3 error: {e}")
        return False
    except (BotoCoreError, Exception) as e:
        print(json.dumps(["status", "no-network"]), flush=True)
        logging.error(f"Network error: {e}")
        return False

def has_network():
    try:
        urllib.request.urlopen('https://aws.amazon.com', timeout=5)
        return True
    except:
        return False

if __name__ == "__main__":
    main()