from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Import functions from other files
from cloudwatch import get_cloudwatch_logs
from guardduty import get_guardduty_findings

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Enable CORS for requests from the Streamlit frontend (adjust origin if needed)
CORS(app)

@app.route('/api/logs', methods=['GET'])
def logs_endpoint():
    """API endpoint to retrieve CloudWatch logs."""
    logs, status_code = get_cloudwatch_logs()
    return jsonify(logs), status_code

@app.route('/api/threats', methods=['GET'])
def threats_endpoint():
    """API endpoint to retrieve GuardDuty findings."""
    threats, status_code = get_guardduty_findings()
    return jsonify(threats), status_code

if __name__ == '__main__':
    # Runs on http://127.0.0.1:5000 by default
    app.run(debug=True) # Set debug=False for production