import boto3
import time
import os
import requests # To get instance metadata
import logging
import json
from datetime import datetime
import uuid # For unique object names

# --- Configuration ---
LOG_FILE_PATH = '/var/log/mock_app.log'
STATE_FILE_PATH = '/var/lib/log_forwarder_state/mock_app.state' # Needs write permission for the user running the script
S3_BUCKET_NAME = 'siemtool-ccs'
# S3 prefix structure: base/instance_id/YYYY/MM/DD/HH/object_name
S3_PREFIX_BASE = 'custom-forwarder-logs'
UPLOAD_INTERVAL_SECONDS = 60 # How often to check for new logs and upload
MAX_BATCH_SIZE_BYTES = 1 * 1024 * 1024 # Upload batch if it reaches 1MB
MAX_BATCH_LINES = 500 # Or upload if it reaches 500 lines
LOG_LEVEL = logging.INFO

# --- Logging Setup ---
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('LogForwarder')

# --- EC2 Metadata ---
METADATA_URL = "http://169.254.169.254/latest/meta-data/"
METADATA_HEADERS = {"X-aws-ec2-metadata-token-ttl-seconds": "21600"} # For IMDSv2
TOKEN_URL = "http://169.254.169.254/latest/api/token"

def get_metadata_token():
    """Gets a session token for IMDSv2."""
    try:
        response = requests.put(TOKEN_URL, headers=METADATA_HEADERS)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not get IMDSv2 token (this is ok for IMDSv1): {e}")
        return None # Fallback for IMDSv1

def get_instance_metadata(path, token):
    """Gets specific metadata from EC2 instance."""
    headers = {}
    if token:
        headers["X-aws-ec2-metadata-token"] = token
    try:
        response = requests.get(METADATA_URL + path, headers=headers, timeout=1.0)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get instance metadata for {path}: {e}")
        return None

# --- State Management ---
def read_last_position(state_file):
    """Reads the last byte offset from the state file."""
    try:
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                content = f.read().strip()
                if content:
                    return int(content)
                else:
                    logger.warning(f"State file '{state_file}' is empty, starting from beginning.")
                    return 0
        else:
             logger.info(f"State file '{state_file}' not found, starting from beginning.")
             return 0
    except (IOError, ValueError) as e:
        logger.error(f"Error reading state file '{state_file}': {e}. Starting from beginning.", exc_info=True)
        return 0

def write_last_position(state_file, position):
    """Writes the last byte offset to the state file."""
    try:
        # Ensure directory exists
        state_dir = os.path.dirname(state_file)
        if not os.path.exists(state_dir):
             logger.info(f"Creating state directory: {state_dir}")
             # Ensure user running script has permission to create/write here
             # Might need sudo setup beforehand if not running as root
             os.makedirs(state_dir, exist_ok=True)

        with open(state_file, 'w') as f:
            f.write(str(position))
    except IOError as e:
        logger.error(f"Error writing state file '{state_file}': {e}", exc_info=True)

# --- S3 Upload ---
def upload_to_s3(s3_client, bucket, prefix, instance_id, content):
    """Uploads log content to S3."""
    now = datetime.utcnow()
    s3_key = os.path.join(
        prefix,
        instance_id,
        now.strftime('%Y'),
        now.strftime('%m'),
        now.strftime('%d'),
        now.strftime('%H'),
        f"{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4()}.log.gz" # Unique filename
    )

    try:
        # Compress content before uploading
        import gzip
        compressed_content = gzip.compress(content.encode('utf-8'))

        logger.info(f"Uploading {len(content.splitlines())} lines ({len(compressed_content)} bytes compressed) to s3://{bucket}/{s3_key}")
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=compressed_content,
            ContentEncoding='gzip',
            ContentType='text/plain' # Or application/json if strictly JSON lines
        )
        return True
    except Exception as e:
        logger.error(f"Failed to upload to s3://{bucket}/{s3_key}: {e}", exc_info=True)
        return False

# --- Main Loop ---
def main():
    logger.info("Starting custom log forwarder.")

    # Get EC2 metadata
    token = get_metadata_token()
    instance_id = get_instance_metadata("instance-id", token)
    region = get_instance_metadata("placement/region", token)

    if not instance_id or not region:
        logger.fatal("Could not retrieve essential instance metadata (ID or Region). Exiting.")
        return

    logger.info(f"Running on Instance ID: {instance_id} in Region: {region}")

    # Initialize S3 client - uses IAM role automatically
    s3_client = boto3.client('s3', region_name=region)

    last_position = read_last_position(STATE_FILE_PATH)
    current_inode = None

    try:
        while True:
            try:
                # Check if log file exists and get its inode
                if not os.path.exists(LOG_FILE_PATH):
                    logger.warning(f"Log file '{LOG_FILE_PATH}' does not exist. Skipping iteration.")
                    time.sleep(UPLOAD_INTERVAL_SECONDS)
                    continue

                stat_info = os.stat(LOG_FILE_PATH)
                file_inode = stat_info.st_ino
                file_size = stat_info.st_size

                # Handle log rotation: if inode changed or size shrunk, reset position
                if current_inode is not None and (file_inode != current_inode or file_size < last_position):
                    logger.info(f"Log rotation detected or file truncated. Resetting position for '{LOG_FILE_PATH}'.")
                    last_position = 0
                current_inode = file_inode

                if file_size > last_position:
                    logger.debug(f"File size ({file_size}) > last position ({last_position}). Reading new lines.")
                    with open(LOG_FILE_PATH, 'r') as f:
                        f.seek(last_position)
                        lines_batch = []
                        batch_size_bytes = 0
                        new_position = last_position

                        while True:
                            line = f.readline()
                            if not line: # Reached end of file
                                break

                            line_bytes = len(line.encode('utf-8'))
                            # Check if adding line exceeds limits
                            if (batch_size_bytes + line_bytes > MAX_BATCH_SIZE_BYTES or
                                len(lines_batch) >= MAX_BATCH_LINES):
                                # Upload current batch before adding new line
                                if lines_batch:
                                    upload_success = upload_to_s3(s3_client, S3_BUCKET_NAME, S3_PREFIX_BASE, instance_id, "".join(lines_batch))
                                    if upload_success:
                                        write_last_position(STATE_FILE_PATH, new_position)
                                        last_position = new_position
                                        lines_batch = []
                                        batch_size_bytes = 0
                                    else:
                                        logger.error("Upload failed, will retry next cycle.")
                                        # Break inner loop to wait before retrying upload
                                        break

                            # Add line to current batch
                            lines_batch.append(line)
                            batch_size_bytes += line_bytes
                            new_position = f.tell() # Update position after successful read

                        # Upload any remaining lines in the last batch
                        if lines_batch:
                             upload_success = upload_to_s3(s3_client, S3_BUCKET_NAME, S3_PREFIX_BASE, instance_id, "".join(lines_batch))
                             if upload_success:
                                 write_last_position(STATE_FILE_PATH, new_position)
                                 last_position = new_position
                             else:
                                 logger.error("Final batch upload failed, will retry next cycle.")
                        elif new_position > last_position:
                            # If we read lines but didn't upload (e.g. small amount), still update state
                            write_last_position(STATE_FILE_PATH, new_position)
                            last_position = new_position


                else:
                    logger.debug("No new lines detected.")

            except FileNotFoundError:
                 logger.warning(f"Log file '{LOG_FILE_PATH}' not found during read attempt.")
                 current_inode = None # Reset inode tracking
                 last_position = 0 # Reset position
            except IOError as e:
                logger.error(f"Error reading log file '{LOG_FILE_PATH}': {e}", exc_info=True)
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}", exc_info=True)

            # Wait before checking again
            logger.debug(f"Sleeping for {UPLOAD_INTERVAL_SECONDS} seconds.")
            time.sleep(UPLOAD_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Log forwarder stopped by user.")
    finally:
        logger.info("Log forwarder exiting.")

if __name__ == "__main__":
    main()
