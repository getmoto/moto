"""Exceptions raised by the Route53 service."""
from moto.core.exceptions import RESTError


class Route53ClientError(RESTError):
    """Base class for Route53 errors."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template", "single_error")
        super().__init__(*args, **kwargs)


class InvalidInput(Route53ClientError):
    """Malformed ARN for the CloudWatch log group."""

    code = 400

    def __init__(self):
        message = "The ARN for the CloudWatch Logs log group is invalid"
        super().__init__("InvalidInput", message)


class NoSuchCloudWatchLogsLogGroup(Route53ClientError):
    """CloudWatch LogGroup is in the permissions policy, but does not exist."""

    code = 404

    def __init__(self):
        message = "The specified CloudWatch Logs log group doesn't exist."
        super().__init__("NoSuchCloudWatchLogsLogGroup", message)


class NoSuchHostedZone(Route53ClientError):
    """HostedZone does not exist."""

    code = 404

    def __init__(self, host_zone_id):
        message = f"No hosted zone found with ID: {host_zone_id}"
        super().__init__("NoSuchHostedZone", message)


class QueryLoggingConfigAlreadyExists(Route53ClientError):
    """Query log config exists for log group and hosted zone combo."""

    code = 409

    def __init__(self):
        message = "A query logging configuration already exists for this hosted zone"
        super().__init__("QueryLoggingConfigAlreadyExists", message)
