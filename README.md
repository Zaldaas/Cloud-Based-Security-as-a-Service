# Cloud-based SIEM Platform

A simple web application demonstrating a cloud-based Security Information and Event Management (SIEM) platform concept using AWS services (CloudWatch Logs and GuardDuty), a Flask backend, and a Streamlit frontend.

## Features

*   **Log Aggregation:** Fetches and displays logs from AWS CloudWatch Logs.
*   **Threat Detection:** Fetches and displays security findings from AWS GuardDuty.
*   **Web Interface:** Provides a user-friendly interface built with Streamlit to view logs and threats.
*   **Search Functionality:** Allows basic text filtering within logs and threats.

## Architecture

*   **Backend:** A Python Flask application (`backend/app.py`) that serves two API endpoints:
    *   `/api/logs`: Retrieves logs from CloudWatch using `backend/cloudwatch.py`.
    *   `/api/threats`: Retrieves findings from GuardDuty using `backend/guardduty.py`.
*   **Frontend:** A Python Streamlit application (`frontend/frontend.py`) that consumes the backend APIs and displays the data in interactive tables within tabs.
*   **AWS Services:** Relies on:
    *   AWS CloudWatch Logs: For storing and retrieving log data.
    *   AWS GuardDuty: For threat detection and security findings.
    *   (Implicitly) AWS IAM: For providing the necessary permissions via access keys.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd Cloud-Based-Security-as-a-Service
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure AWS Credentials and Settings:**
    *   Create a `.env` file in the `backend/` directory.
    *   Add the following environment variables to the `.env` file, replacing the placeholder values with your actual AWS details:
        ```dotenv
        AWS_REGION=<your_aws_region> # e.g., us-east-1
        AWS_ACCESS_KEY_ID=<your_aws_access_key_id>
        AWS_SECRET_ACCESS_KEY=<your_aws_secret_access_key>
        AWS_LOG_GROUP_NAME=<your_cloudwatch_log_group_name>
        AWS_LOG_STREAM_NAME=<your_cloudwatch_log_stream_name>
        ```
    *   **Important:** Ensure the AWS credentials have the necessary permissions to:
        *   `logs:GetLogEvents` for the specified CloudWatch Log Group and Stream.
        *   `guardduty:ListDetectors`, `guardduty:ListFindings`, `guardduty:GetFindings` for GuardDuty in the specified region.

4.  **Run the Backend:**
    *   Navigate to the backend directory: `cd backend`
    *   Start the Flask server: `python app.py`
    *   The backend will run on `http://127.0.0.1:5000` by default.

5.  **Run the Frontend:**
    *   Open a *new* terminal window.
    *   Navigate to the frontend directory: `cd frontend`
    *   Start the Streamlit application: `streamlit run frontend.py`
    *   The frontend will open in your web browser, usually at `http://localhost:8501`.

## Usage

*   Open the Streamlit application URL in your browser.
*   Use the "Logs" tab to view CloudWatch logs.
*   Use the "Threats" tab to view GuardDuty findings.
*   Use the search bars within each tab to filter the displayed data.

## Dependencies

*   Flask
*   Flask-Cors
*   Streamlit
*   boto3
*   requests
*   pandas
*   python-dotenv

