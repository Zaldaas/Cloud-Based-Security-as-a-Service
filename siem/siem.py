import requests
import json
from datetime import datetime, timedelta, timezone
import sys

# --- Configuration ---
# !!! REPLACE THIS WITH YOUR ACTUAL API GATEWAY INVOKE URL !!!
API_BASE_URL = "https://vebsnzh5ob.execute-api.us-east-2.amazonaws.com" # Replace with your URL
API_ENDPOINT = "/logs" # The route path you configured

# --- API Call Function (Copied from api_caller_script_v1) ---
def fetch_logs(base_url, endpoint, params=None):
    """Calls the API Gateway endpoint to fetch logs."""
    # Construct the full URL
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    # Standard headers for JSON APIs
    headers = {'Accept': 'application/json'}

    # Filter out None values from params before making the request
    filtered_params = {k: v for k, v in params.items() if v is not None} if params else None

    print(f"Calling API: {full_url}")
    print(f"With parameters: {json.dumps(filtered_params) if filtered_params else 'Default (Last Hour)'}") # Modified print statement

    try:
        # Make the GET request with parameters and a timeout
        response = requests.get(full_url, headers=headers, params=filtered_params, timeout=60) # 60-second timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        print(f"API Status Code: {response.status_code}")

        # Try to parse JSON, handle potential errors
        try:
            return response.json() # Returns a Python dictionary
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response from API.", file=sys.stderr)
            print("Raw Response Text:", response.text[:500], file=sys.stderr) # Print first 500 chars of error
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}", file=sys.stderr)
        print(f"Response Content: {response.text}", file=sys.stderr)
        return None
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}", file=sys.stderr)
        return None
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected error occurred during the request: {req_err}", file=sys.stderr)
        return None

# --- Example Usage within another script ---
if __name__ == "__main__":
    print("Example: Fetching logs from the last hour...")

    # Define parameters directly in the script
    # To fetch the last hour, we pass None for start/end times
    # The Lambda function applies the default logic
    call_params = {
        "start_time": None,
        "end_time": None,
        "instance_id": None # Set to an instance ID string if needed, or leave as None for all
    }

    # Call the function to get the logs
    log_data = fetch_logs(API_BASE_URL, API_ENDPOINT, params=call_params)

    # Process the result
    if log_data and 'logs' in log_data:
        print(f"\nSuccessfully fetched {log_data.get('count', 0)} log entries.")
        # You can now iterate through the logs or process the data
        for log_entry in log_data['logs']:
             # Example: Print just the message field
             print(f"  - {log_entry.get('message')}")
             # Or access other fields: log_entry.get('timestamp'), log_entry.get('user'), etc.

        # Example: Print the full response structure again
        # print("\n--- Full API Response ---")
        # print(json.dumps(log_data, indent=2))

    else:
        print("\nFailed to fetch logs or no logs found.")

    # --- Example: Fetching logs for a specific time range and instance ---
    print("\nExample: Fetching logs for a specific time and instance...")

    specific_params = {
        "start_time": "2025-04-29T00:18:00Z", # Example start time
        "end_time": "2025-04-29T00:20:00Z",   # Example end time
        "instance_id": "i-095abc5bf9b3d41a3" # Example instance ID
    }

    specific_log_data = fetch_logs(API_BASE_URL, API_ENDPOINT, params=specific_params)

    if specific_log_data and 'logs' in specific_log_data:
         print(f"\nSuccessfully fetched {specific_log_data.get('count', 0)} specific log entries.")
         # Process these logs as needed
         # print(json.dumps(specific_log_data, indent=2))
    else:
        print("\nFailed to fetch specific logs or no logs found.")

