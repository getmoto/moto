from time import time

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID


@mock_aws
@pytest.mark.parametrize("identifier_type", ["name", "arn"])
def test_log_group_identifier_selects_the_requested_group(identifier_type):
    client = boto3.client("logs", region_name="us-east-1")
    for name in ["first", "second"]:
        client.create_log_group(logGroupName=name)
        client.create_log_stream(logGroupName=name, logStreamName=name)
        client.put_log_events(
            logGroupName=name,
            logStreamName=name,
            logEvents=[{"timestamp": int(time() * 1000), "message": name}],
        )

    identifier = "first"
    if identifier_type == "arn":
        identifier = f"arn:aws:logs:us-east-1:{DEFAULT_ACCOUNT_ID}:log-group:first"

    streams = client.describe_log_streams(logGroupIdentifier=identifier)["logStreams"]
    assert [stream["logStreamName"] for stream in streams] == ["first"]
    events = client.get_log_events(
        logGroupIdentifier=identifier, logStreamName="first"
    )["events"]
    assert [event["message"] for event in events] == ["first"]


@mock_aws
@pytest.mark.parametrize("identifier_type", ["name", "arn"])
@pytest.mark.parametrize("operation", ["describe_log_streams", "get_log_events"])
def test_unknown_log_group_identifier_does_not_select_another_group(
    identifier_type, operation
):
    client = boto3.client("logs", region_name="us-east-1")
    client.create_log_group(logGroupName="existing")
    client.create_log_stream(logGroupName="existing", logStreamName="stream")
    identifier = "missing"
    if identifier_type == "arn":
        identifier = f"arn:aws:logs:us-east-1:{DEFAULT_ACCOUNT_ID}:log-group:missing"
    kwargs = {"logGroupIdentifier": identifier}
    if operation == "get_log_events":
        kwargs["logStreamName"] = "stream"
    with pytest.raises(ClientError) as exc:
        getattr(client, operation)(**kwargs)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
