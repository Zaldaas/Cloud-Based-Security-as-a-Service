import boto3
import os
from datetime import datetime

def get_guardduty_findings():
    """
    Fetches GuardDuty findings for the specified AWS region.
    """
    try:
        # Use environment variables for configuration
        region_name = os.getenv('AWS_REGION')
        aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

        if not all([region_name, aws_access_key_id, aws_secret_access_key]):
             return {"error": "Missing AWS configuration in environment variables."}, 500

        # Initialize Boto3 client for GuardDuty
        guardduty_client = boto3.client(
            'guardduty',
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

        # 1. Find the DetectorId
        detector_response = guardduty_client.list_detectors()
        detector_ids = detector_response.get('DetectorIds', [])

        if not detector_ids:
            return {"message": "No GuardDuty detectors found in this region."}, 200 # Or 404 if preferred

        detector_id = detector_ids[0] # Assuming only one detector per region

        # 2. List Finding IDs (get recent ones, adjust sort criteria/filters as needed)
        finding_response = guardduty_client.list_findings(
            DetectorId=detector_id,
            FindingCriteria={
                'Criterion': {
                    # Example: Filter for non-archived findings
                     'severity': { # Could filter by severity here if needed
                        'Gte': 1 # Get all severities (1-10 approx)
                    },
                    'service.archived': {
                         'Eq': ['false']
                     }
                }
            },
             SortCriteria={
                 'AttributeName': 'updatedAt',
                 'OrderBy': 'DESC' # Get most recent first
             },
             MaxResults=50 # Limit the number of findings returned initially
        )

        finding_ids = finding_response.get('FindingIds', [])

        if not finding_ids:
            return {"message": "No active GuardDuty findings found matching criteria."}, 200

        # 3. Get Finding Details
        findings_details_response = guardduty_client.get_findings(
            DetectorId=detector_id,
            FindingIds=finding_ids
        )

        findings = findings_details_response.get('Findings', [])

        # Format findings for easier frontend use
        formatted_findings = []
        for finding in findings:
            formatted_finding = {
                "id": finding.get('Id'),
                "arn": finding.get('Arn'),
                "type": finding.get('Type'),
                "severity": finding.get('Severity'), # Severity is numeric
                "title": finding.get('Title'),
                "description": finding.get('Description'),
                "region": finding.get('Region'),
                "created_at": finding.get('CreatedAt'), # Already in ISO 8601 format
                "updated_at": finding.get('UpdatedAt'),
                # Extract key resource details if available
                "resource_type": finding.get('Resource', {}).get('ResourceType'),
                # Example: Get instance ID if it's an EC2 finding
                "instance_id": finding.get('Resource', {}).get('InstanceDetails', {}).get('InstanceId'),
                # Example: Get affected access key if relevant
                 "access_key_id": finding.get('Resource', {}).get('AccessKeyDetails', {}).get('AccessKeyId'),
                 "user_name": finding.get('Resource', {}).get('AccessKeyDetails', {}).get('UserName'),
                # Add more relevant fields as needed
            }
            # Clean up None values if desired, though None might be informative
            # formatted_finding = {k: v for k, v in formatted_finding.items() if v is not None}
            formatted_findings.append(formatted_finding)


        # Add pagination handling here for list_findings if needed

        return formatted_findings, 200

    except Exception as e:
        print(f"Error fetching GuardDuty findings: {e}") # Log detailed error server-side
        return {"error": f"An error occurred fetching GuardDuty findings: {str(e)}"}, 500