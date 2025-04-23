import logging
import time
import random
import json
from datetime import datetime

# --- Configuration ---
LOG_FILE = '/var/log/mock_app.log'  # Log file path (ensure permissions allow writing)
LOG_LEVEL = logging.INFO         # Logging level (e.g., INFO, WARNING, ERROR)
SIMULATION_DURATION_SECONDS = 300 # How long the simulation runs (e.g., 300 seconds = 5 minutes)
MIN_DELAY_SECONDS = 0.5           # Minimum delay between actions
MAX_DELAY_SECONDS = 3.0           # Maximum delay between actions

# --- Mock Data ---
USERNAMES = ["alice", "bob", "charlie", "david", "eve", "frank", "grace"]
SOURCE_IPS = ["192.168.1.10", "10.0.0.5", "172.16.3.22", "203.0.113.45", "198.51.100.7", "8.8.8.8", "1.1.1.1"]
RESOURCES = ["/api/v1/data", "/api/v1/profile", "/api/v1/settings", "/admin/dashboard", "/public/report"]
ACTIONS = ["login", "logout", "read_data", "write_data", "update_profile", "access_denied", "transaction_process"]
TRANSACTION_STATUS = ["SUCCESS", "FAILED_INSUFFICIENT_FUNDS", "FAILED_TIMEOUT", "FAILED_INVALID_ITEM"]

# --- Logging Setup ---
# Use JSON formatter for structured logs, easily parsable by SIEM tools
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "source_ip": getattr(record, 'source_ip', 'N/A'),
            "user": getattr(record, 'user', 'N/A'),
            "action": getattr(record, 'action', 'N/A'),
            "status": getattr(record, 'status', 'N/A'),
            "resource": getattr(record, 'resource', 'N/A'),
            "transaction_id": getattr(record, 'transaction_id', 'N/A'),
            "details": getattr(record, 'details', 'N/A')
        }
        # Remove keys with 'N/A' values for cleaner logs
        log_record = {k: v for k, v in log_record.items() if v != 'N/A'}
        return json.dumps(log_record)

# Configure root logger
logger = logging.getLogger('MockAppLogger')
logger.setLevel(LOG_LEVEL)

# Create file handler
try:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(LOG_LEVEL)

    # Create and set formatter
    formatter = JsonFormatter(datefmt='%Y-%m-%dT%H:%M:%S.%fZ') # ISO 8601 format often preferred
    file_handler.setFormatter(formatter)

    # Add handler to the logger
    logger.addHandler(file_handler)

    # Optional: Add a stream handler to also print logs to console
    # stream_handler = logging.StreamHandler()
    # stream_handler.setFormatter(formatter)
    # logger.addHandler(stream_handler)

except IOError as e:
    print(f"Error: Could not open log file '{LOG_FILE}'. Please check path and permissions. {e}")
    # Optionally, fall back to console logging only
    logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__) # Use standard logger if file fails
    logger.error(f"Failed to initialize file logging to {LOG_FILE}", exc_info=True)


# --- Mock Business Functions ---

def simulate_user_login():
    """Simulates a user login attempt."""
    user = random.choice(USERNAMES)
    ip = random.choice(SOURCE_IPS)
    success = random.choices([True, False], weights=[90, 10], k=1)[0] # 90% success rate

    log_data = {'user': user, 'source_ip': ip, 'action': 'login'}
    if success:
        log_data['status'] = 'SUCCESS'
        logger.info(f"User '{user}' logged in successfully.", extra=log_data)
    else:
        log_data['status'] = 'FAILED'
        logger.warning(f"User '{user}' failed login attempt.", extra=log_data)

def simulate_data_access():
    """Simulates accessing a data resource."""
    user = random.choice(USERNAMES)
    ip = random.choice(SOURCE_IPS)
    resource = random.choice(RESOURCES)
    action_type = random.choice(["read_data", "write_data"])
    allowed = random.choices([True, False], weights=[85, 15], k=1)[0] # 85% allowed rate

    log_data = {'user': user, 'source_ip': ip, 'action': action_type, 'resource': resource}
    if allowed:
        log_data['status'] = 'SUCCESS'
        logger.info(f"User '{user}' {action_type.replace('_',' ')} on resource '{resource}'.", extra=log_data)
    else:
        log_data['status'] = 'ACCESS_DENIED'
        logger.error(f"User '{user}' denied access for {action_type.replace('_',' ')} on resource '{resource}'.", extra=log_data)

def simulate_transaction():
    """Simulates processing a transaction."""
    user = random.choice(USERNAMES)
    ip = random.choice(SOURCE_IPS)
    transaction_id = f"txn_{int(time.time())}_{random.randint(1000, 9999)}"
    status = random.choice(TRANSACTION_STATUS)

    log_data = {
        'user': user,
        'source_ip': ip,
        'action': 'transaction_process',
        'transaction_id': transaction_id,
        'status': status
    }
    if status == "SUCCESS":
        amount = round(random.uniform(5.0, 500.0), 2)
        log_data['details'] = f"amount: {amount}"
        logger.info(f"Transaction '{transaction_id}' processed successfully for user '{user}'. Amount: ${amount}", extra=log_data)
    else:
        logger.warning(f"Transaction '{transaction_id}' failed for user '{user}'. Reason: {status}", extra=log_data)

# --- Main Simulation Loop ---
if __name__ == "__main__":
    logger.info("Starting mock application simulation.", extra={'action': 'simulation_start'})
    start_time = time.time()

    try:
        while time.time() - start_time < SIMULATION_DURATION_SECONDS:
            # Choose a random action to simulate
            action_func = random.choice([
                simulate_user_login,
                simulate_data_access,
                simulate_transaction
            ])

            # Execute the chosen action
            action_func()

            # Wait for a random delay before the next action
            delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            time.sleep(delay)

    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user.", extra={'action': 'simulation_stop', 'status': 'INTERRUPTED'})
    except Exception as e:
         logger.error(f"An unexpected error occurred during simulation: {e}", exc_info=True, extra={'action': 'simulation_error'})
    finally:
        end_time = time.time()
        total_duration = end_time - start_time
        logger.info(f"Mock application simulation finished. Duration: {total_duration:.2f} seconds.", extra={'action': 'simulation_end', 'status': 'COMPLETED', 'duration_seconds': round(total_duration, 2)})

