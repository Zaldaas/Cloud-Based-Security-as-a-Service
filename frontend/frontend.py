import streamlit as st
import requests
import pandas as pd
import json # Import json for potential error message parsing
import re # Import re for title conversion
from streamlit_autorefresh import st_autorefresh # Import the autorefresh component

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:5000" # Default Flask dev server URL

# --- Page Setup ---
st.set_page_config(page_title="Cloud SIEM Platform", layout="wide")

st.title("☁️ Cloud-based SIEM Platform")
st.caption("Real-time threat detection and comprehensive security monitoring on AWS infrastructure.")

# --- Helper Functions ---
def fetch_data(endpoint):
    """Fetches data from the backend API."""
    try:
        response = requests.get(f"{BACKEND_URL}{endpoint}")
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Connection Error: Could not connect to the backend at {BACKEND_URL}. Is the backend running?")
        return None
    except requests.exceptions.Timeout:
        st.error("Error: The request to the backend timed out.")
        return None
    except requests.exceptions.RequestException as e:
        # Try to parse potential JSON error message from backend
        error_detail = ""
        try:
            error_json = e.response.json()
            if isinstance(error_json, dict) and 'error' in error_json:
                 error_detail = f": {error_json['error']}"
            elif isinstance(error_json, dict) and 'message' in error_json: # Handle info messages too
                 error_detail = f": {error_json['message']}"
            else:
                 error_detail = f": {e.response.text}" # Fallback to raw text
        except:
             error_detail = f": {str(e)}" # Fallback if response is not JSON

        st.error(f"Error fetching data from {endpoint}{error_detail}")
        return None
    except json.JSONDecodeError as err: # Added 'err' variable
         st.error(f"Error: Could not decode the response from {endpoint}. Received: {response.text[:200]}... Error: {err}") # Show part of response and error
         return None

def snake_to_title(snake_str):
    """Converts snake_case or camelCase to Title Case."""
    if not isinstance(snake_str, str):
        return str(snake_str) # Return string representation if not a string
    # Add space before capital letters (for camelCase)
    s = re.sub(r"(\w)([A-Z])", r"\1 \2", snake_str)
    # Replace underscores with spaces and capitalize words
    return s.replace('_', ' ').title()

def style_severity(val):
    """Applies background color based on severity label."""
    val_lower = str(val).lower()
    if 'low' in val_lower:
        color = 'yellow'
    elif 'medium' in val_lower:
        color = 'orange'
    elif 'high' in val_lower:
        color = 'red'
    elif 'critical' in val_lower:
        color = 'darkred'; # Use darkred for critical for visibility
        return f'background-color: {color}; color: white;' # Add white text for darkred
    else:
        color = '' # No style for others (e.g., Informational, Unknown)

    return f'background-color: {color}' if color else ''

def display_dataframe(data, search_term, column_order, date_columns, data_type=None):
    """Displays data in a searchable, formatted Pandas DataFrame with optional styling."""
    if not data:
        st.info("No data available.")
        return

    if isinstance(data, dict) and ('error' in data or 'message' in data):
        if 'error' in data:
             st.error(f"Backend Error: {data['error']}")
        elif 'message' in data:
             st.info(f"Backend Message: {data['message']}")
        return

    try:
        df = pd.DataFrame(data)

        if df.empty:
            st.info("No data matches the criteria.")
            return

        # Format date columns
        for col in date_columns:
            if col in df.columns:
                try:
                    # Convert to datetime, coercing errors, then format
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
                    # Replace NaT (Not a Time) that results from coercion errors with empty string or original value
                    df[col] = df[col].fillna('') # Or handle as needed
                except Exception as date_e:
                     st.warning(f"Could not format date column '{col}': {date_e}") # Warn if formatting fails

        # Rename columns to Title Case
        rename_map = {col: snake_to_title(col) for col in df.columns}
        df.rename(columns=rename_map, inplace=True)

        # Filter columns based on display order, maintaining Title Case
        display_columns_title_case = [snake_to_title(col) for col in column_order if snake_to_title(col) in df.columns]

        if not display_columns_title_case:
            st.warning("No columns available for display after processing.")
            return

        df_display = df[display_columns_title_case]


        # Basic Search/Filter (applied AFTER formatting and column selection)
        if search_term:
            # Simple string search across the *displayed* columns (case-insensitive)
            df_str = df_display.astype(str).apply(lambda row: ' '.join(row).lower(), axis=1)
            df_display = df_display[df_str.str.contains(search_term.lower())]

        # Apply styling if applicable
        if data_type == 'threats' and 'Severity' in df_display.columns:
            styler = df_display.style.applymap(style_severity, subset=['Severity'])
            st.dataframe(styler, use_container_width=True)
        else:
            st.dataframe(df_display, use_container_width=True) # Display the formatted and ordered dataframe

    except Exception as e:
        st.error(f"Error displaying data: {e}")
        st.write("Received data structure (first 5 items):")
        st.json(data[:5] if isinstance(data, list) else data) # Show partial raw data if DataFrame processing fails


# --- Main Application ---

# Define column orders and date columns
LOGS_COLUMN_ORDER = [
    'action', 'ingestionTime', 'level', 'message',
    'source_ip', 'status', 'user', 'resource', 'transactionId', 'details'
]
LOGS_DATE_COLUMNS = ['ingestionTime']

THREATS_COLUMN_ORDER = [
    'title', 'created_at', 'updated_at', 'description', 'severity', 'type',
    'resource_type', 'id', 'instance_id', 'arn', 'access_key_id', 'region', 'user_name'
]
THREATS_DATE_COLUMNS = ['created_at', 'updated_at']

tab1, tab2 = st.tabs(["📊 Logs", "🛡️ Threats"])

with tab1:
    st.header("CloudWatch Logs")
    search_logs = st.text_input("Search Logs", key="log_search", placeholder="Enter keyword to filter logs...")

    # Auto-refresh this tab every 10 seconds (10000 milliseconds)
    st_autorefresh(interval=10 * 1000, key="logfetchrefresh")

    logs_data = fetch_data("/api/logs")

    if logs_data is not None:
        # Ensure it's a list before passing
        display_data = logs_data if isinstance(logs_data, list) else []
        display_dataframe(display_data, search_logs, LOGS_COLUMN_ORDER, LOGS_DATE_COLUMNS, data_type='logs')
    else:
        # Error message already displayed by fetch_data
        pass


with tab2:
    st.header("GuardDuty Threats")
    search_threats = st.text_input("Search Threats", key="threat_search", placeholder="Enter keyword to filter threats...")
    threats_data = fetch_data("/api/threats")

    processed_threats_data = [] # Initialize as empty list
    if threats_data is not None:
         # Attempt to provide more meaningful severity display
        if isinstance(threats_data, list) and threats_data:
             try:
                # Define severity mapping (simplified labels)
                 severity_label_map = {
                    0: "Informational", # Added for potential 0 value
                    1: "Low", 2: "Low", 3: "Low",
                    4: "Medium", 5: "Medium", 6: "Medium",
                    7: "High", 8: "High",
                    9: "Critical", 10: "Critical" # Assuming 9 and 10 exist
                 }
                 # Process data before converting to DataFrame for display
                 processed_threats_data = []
                 for finding in threats_data:
                     # Make a copy to avoid modifying original data if fetched again
                     processed_finding = finding.copy()
                     if 'severity' in processed_finding:
                         original_severity = processed_finding['severity']
                         # Map the severity number to a label, keep original number if not found
                         processed_finding['severity'] = severity_label_map.get(original_severity, f"Unknown ({original_severity})")
                     processed_threats_data.append(processed_finding)

             except Exception as e:
                st.warning(f"Could not map severity levels: {e}")
                processed_threats_data = threats_data # Use original data if processing fails

        elif isinstance(threats_data, dict): # Handle potential error dict passed
             processed_threats_data = threats_data # Pass dict directly to display_dataframe for error handling

        # Display the processed data
        display_dataframe(processed_threats_data, search_threats, THREATS_COLUMN_ORDER, THREATS_DATE_COLUMNS, data_type='threats')
    else:
        # Error message already displayed by fetch_data
        pass