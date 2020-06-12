from __future__ import unicode_literals
import boto3
from freezegun import freeze_time
import sure  # noqa
import re

from moto import mock_opsworks


@freeze_time("2015-01-01")
@mock_opsworks
def test_create_app_response():
    client = boto3.client("opsworks", region_name="us-east-1")
    stack_id = client.create_stack(
        Name="test_stack_1",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn",
    )["StackId"]

    response = client.create_app(StackId=stack_id, Type="other", Name="TestApp")

    response.should.contain("AppId")

    second_stack_id = client.create_stack(
        Name="test_stack_2",
        Region="us-east-1",
        ServiceRoleArn="service_arn",
        DefaultInstanceProfileArn="profile_arn",
    )["StackId"]

    response = client.create_app(StackId=second_stack_id, Type="other", Name="TestApp")

    response.should.contain("AppId")

    # ClientError
    client.create_app.when.called_with(
        StackId=stack_id, Type="other", Name="TestApp"
    ).should.throw(Exception, re.compile(r'already an app named "TestApp"'))

    # ClientError
    client.create_app.when.called_with(
        StackId="nothere", Type="other", Name="TestApp"
    ).should.throw(Exception, "nothere")


@freeze_time("2015-01-01")
@mock_opsworks
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
    rv1["Apps"].should.equal(rv2["Apps"])

    rv1["Apps"][0]["Name"].should.equal("TestApp")

    # ClientError
    client.describe_apps.when.called_with(
        StackId=stack_id, AppIds=[app_id]
    ).should.throw(Exception, "Please provide one or more app IDs or a stack ID")
    # ClientError
    client.describe_apps.when.called_with(StackId="nothere").should.throw(
        Exception, "Unable to find stack with ID nothere"
    )
    # ClientError
    client.describe_apps.when.called_with(AppIds=["nothere"]).should.throw(
        Exception, "nothere"
    )
