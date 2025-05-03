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

        events = []
        next_token = None

        while True:
            kwargs = {
                'logGroupName': log_group_name,
                'logStreamName': log_stream_name,
                'startFromHead': True,
                'limit': 1000 # Keep limit per request reasonable
            }
            if next_token:
                kwargs['nextToken'] = next_token

            try:
                response = logs_client.get_log_events(**kwargs)
            except logs_client.exceptions.ResourceNotFoundException:
                 # Check for ResourceNotFoundException specifically for get_log_events
                 # Might happen if stream was deleted between checks or initial list
                 if not events: # If no events were fetched at all, it's a 404
                     return {"error": f"Log stream '{log_stream_name}' not found in group '{log_group_name}'."}, 404
                 else: # If some events were fetched, just stop pagination
                     print(f"Warning: Log stream '{log_stream_name}' disappeared during pagination.")
                     break # Exit the loop, return what we have
            except Exception as e:
                 # Catch other potential errors during get_log_events
                 print(f"Error during get_log_events pagination: {e}")
                 # Return error only if we haven't fetched any events yet
                 if not events:
                     return {"error": f"An error occurred fetching CloudWatch logs: {str(e)}"}, 500
                 else:
                     break # Exit the loop

            events.extend(response.get('events', []))

            # Check if the same token is returned, indicating end of stream
            returned_token = response.get('nextForwardToken')
            if returned_token == next_token or not returned_token:
                break # No more pages

            next_token = returned_token
            # Optional: Add a small delay to avoid potential rate limiting
            # import time
            # time.sleep(0.1)


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