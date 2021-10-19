"""Exceptions raised by the Route53 service."""
from moto.core.exceptions import JsonRESTError


class InvalidInput(JsonRESTError):
    """Malformed ARN for the CloudWatch log group."""

    code = 400

    def __init__(self):
        message = "The ARN for the CloudWatch Logs log group is invalid"
        super().__init__("InvalidInput", message)


class NoSuchHostedZone(JsonRESTError):
    """HostedZone does not exist."""

    code = 400

    def __init__(self, host_zone_id):
        message = f"No hosted zone found with ID: {host_zone_id}"
        super().__init__("NoSuchHostedZone", message)


class NoSuchCloudWatchLogsLogGroup(JsonRESTError):
    """CloudWatch LogGroup is in the permissions policy, but does not exist."""

    code = 400

    def __init__(self):
        message = "The specified CloudWatch Logs log group doesn't exist."
        super().__init__("NoSuchCloudWatchLogsLogGroup", message)
