import boto3
import os
import json
from datetime import datetime

def get_cloudwatch_logs():
    """
    Fetches log events from the specified CloudWatch Log Stream.
    Parses JSON messages into dictionaries.
    """
    try:
        # Use environment variables for configuration
        region_name = os.getenv('AWS_REGION')
        log_group_name = os.getenv('AWS_LOG_GROUP_NAME')
        log_stream_name = os.getenv('AWS_LOG_STREAM_NAME')
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

        if not all([region_name, log_group_name, log_stream_name, aws_access_key_id, aws_secret_access_key]):
             return {"error": "Missing AWS configuration in environment variables."}, 500

        # Initialize Boto3 client for CloudWatch Logs
        logs_client = boto3.client(
            'logs',
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

        # Fetch log events
        # startFromHead=True gets older events first. Remove or set to False for newest first.
        # limit can be adjusted as needed.
        response = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            startFromHead=True, # Get logs from the beginning of the stream
            limit=1000 # Adjust as needed, max 10000
        )

        events = response.get('events', [])
        formatted_logs = []

        for event in events:
            try:
                # The message from business.py is a JSON string
                log_data = json.loads(event['message'])
                # Add the ingestion time from CloudWatch if needed
                log_data['ingestionTime'] = datetime.fromtimestamp(event['ingestionTime'] / 1000).isoformat()
                # Ensure timestamp from the log itself is present
                if 'timestamp' not in log_data and 'timestamp' in event:
                     log_data['original_timestamp'] = datetime.fromtimestamp(event['timestamp'] / 1000).isoformat()
                formatted_logs.append(log_data)
            except json.JSONDecodeError:
                # Handle cases where a log message isn't valid JSON
                formatted_logs.append({
                    "timestamp": datetime.fromtimestamp(event['timestamp'] / 1000).isoformat(),
                    "ingestionTime": datetime.fromtimestamp(event['ingestionTime'] / 1000).isoformat(),
                    "message": event['message'],
                    "level": "RAW", # Indicate it wasn't parsed
                })
            except Exception as e:
                 print(f"Error processing single log event: {e}") # Log error server-side
                 formatted_logs.append({
                    "timestamp": datetime.fromtimestamp(event['timestamp'] / 1000).isoformat(),
                    "ingestionTime": datetime.fromtimestamp(event['ingestionTime'] / 1000).isoformat(),
                    "message": event['message'],
                    "level": "ERROR",
                    "details": f"Parsing error: {e}"
                 })


        # Add pagination handling here if needed using 'nextForwardToken'

        return formatted_logs, 200

    except logs_client.exceptions.ResourceNotFoundException:
        return {"error": f"Log group '{log_group_name}' or stream '{log_stream_name}' not found."}, 404
    except Exception as e:
        print(f"Error fetching CloudWatch logs: {e}") # Log detailed error server-side
        return {"error": f"An error occurred fetching CloudWatch logs: {str(e)}"}, 500