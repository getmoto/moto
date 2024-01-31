import boto3
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_aws


@freeze_time("2015-01-01")
@mock_aws
def test_create_app_response():
    client = boto3.client("opsworks", region_name="us-east-1")
    stack_id = client.create_stack(
        Name="test_stack_1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn",
    )["StackId"]

    response = client.create_app(StackId=stack_id, Type="other", Name="TestApp")

    assert "AppId" in response

    second_stack_id = client.create_stack(
        Name="test_stack_2",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn",
    )["StackId"]

    response = client.create_app(StackId=second_stack_id, Type="other", Name="TestApp")

    assert "AppId" in response

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.create_app(StackId=stack_id, Type="other", Name="TestApp")
    assert r'already an app named "TestApp"' in exc.value.response["Error"]["Message"]

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.create_app(StackId="nothere", Type="other", Name="TestApp")
    assert exc.value.response["Error"]["Message"] == "nothere"


@freeze_time("2015-01-01")
@mock_aws
def test_describe_apps():
    client = boto3.client("opsworks", region_name="us-east-1")
    stack_id = client.create_stack(
        Name="test_stack_1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn",
    )["StackId"]
    app_id = client.create_app(StackId=stack_id, Type="other", Name="TestApp")["AppId"]

    rv1 = client.describe_apps(StackId=stack_id)
    rv2 = client.describe_apps(AppIds=[app_id])
    assert rv1["Apps"] == rv2["Apps"]

    assert rv1["Apps"][0]["Name"] == "TestApp"

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.describe_apps(StackId=stack_id, AppIds=[app_id])
    assert exc.value.response["Error"]["Message"] == (
        "Please provide one or more app IDs or a stack ID"
    )

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.describe_apps(StackId="nothere")
    assert exc.value.response["Error"]["Message"] == (
        "Unable to find stack with ID nothere"
    )

    # ClientError
    with pytest.raises(ClientError) as exc:
        client.describe_apps(AppIds=["nothere"])
    assert exc.value.response["Error"]["Message"] == "nothere"
