import requests
import json
import argparse
from datetime import datetime, timezone
import sys

# --- Configuration ---
# !!! REPLACE THIS WITH YOUR ACTUAL API GATEWAY INVOKE URL !!!
API_BASE_URL = "https://vebsnzh5ob.execute-api.us-east-2.amazonaws.com" # Replace with your URL
API_ENDPOINT = "/logs" # The route path you configured

# --- Argument Parsing ---
def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Fetch logs via the SIEM Log API.")
    parser.add_argument(
        "--start-time",
        help="Start time in ISO 8601 UTC format (e.g., 2025-04-29T00:00:00Z)",
        type=str,
        default=None
    )
    parser.add_argument(
        "--end-time",
        help="End time in ISO 8601 UTC format (e.g., 2025-04-29T01:00:00Z)",
        type=str,
        default=None
    )
    parser.add_argument(
        "--instance-id",
        help="Specific EC2 instance ID to filter logs for (e.g., i-012345abcdef)",
        type=str,
        default=None
    )
    parser.add_argument(
        "--output-file",
        help="Optional file path to save the JSON output",
        type=str,
        default=None
    )
    return parser.parse_args()

# --- API Call ---
def fetch_logs(base_url, endpoint, params=None):
    """Calls the API Gateway endpoint to fetch logs."""
    # Construct the full URL
    full_url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    # Standard headers for JSON APIs
    headers = {'Accept': 'application/json'}

    # Filter out None values from params before making the request
    filtered_params = {k: v for k, v in params.items() if v is not None} if params else None

    print(f"Calling API: {full_url}")
    print(f"With parameters: {json.dumps(filtered_params) if filtered_params else 'None'}")

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

# --- Main Execution ---
if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_arguments()

    # Prepare parameters dictionary for the API call
    api_params = {
        "start_time": args.start_time,
        "end_time": args.end_time,
        "instance_id": args.instance_id
    }

    # Fetch the logs from the API
    result_data = fetch_logs(API_BASE_URL, API_ENDPOINT, params=api_params)

    # Process the result
    if result_data:
        print("\n--- API Response ---")
        # Pretty print the JSON response to the console
        print(json.dumps(result_data, indent=2))

