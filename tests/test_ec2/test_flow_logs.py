from __future__ import unicode_literals

# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises  # noqa
from nose.tools import assert_raises

import boto3
#boto3.set_stream_logger(name='botocore')
import boto
import boto.vpc
from boto.exception import EC2ResponseError
from botocore.exceptions import ParamValidationError, ClientError
import json
import sure  # noqa
import random
import sys

from moto import mock_cloudformation_deprecated, mock_ec2, mock_ec2_deprecated, mock_s3
from moto.core import ACCOUNT_ID

@mock_s3
@mock_ec2
def test_flow_logs_create():
    s3 = boto3.resource("s3", region_name="us-west-1")
    ec2_conn = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    with assert_raises(ClientError) as ex:
        ec2_conn.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
            LogDestination="arn:aws:s3:::" + bucket.name,
            DryRun=True,
        )
    ex.exception.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.exception.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateFlowLogs operation: Request would have succeeded, but DryRun flag is set"
    )

    response = ec2_conn.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    response.should.have.length_of(1)

    flow_logs = ec2_conn.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(1)

    flow_log = flow_logs[0]

    flow_log["FlowLogId"].should.equal(response[0])
    flow_log["DeliverLogsStatus"].should.equal("SUCCESS")
    flow_log["FlowLogStatus"].should.equal("ACTIVE")
    flow_log["ResourceId"].should.equal(vpc["VpcId"])
    flow_log["TrafficType"].should.equal("ALL")
    flow_log["LogDestinationType"].should.equal("s3")
    flow_log["LogDestination"].should.equal("arn:aws:s3:::" + bucket.name)
    flow_log["LogFormat"].should.equal("${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}")
    flow_log["MaxAggregationInterval"].should.equal(600)


@mock_s3
@mock_ec2
def test_flow_log_create_many():
    s3 = boto3.resource("s3", region_name="us-west-1")
    ec2_conn = boto3.client("ec2", region_name="us-west-1")

    vpc_1 = ec2_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc_2 = ec2_conn.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    response = ec2_conn.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc_1["VpcId"],vpc_2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
        LogFormat="${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}",
    )["FlowLogIds"]
    response.should.have.length_of(2)

    flow_logs = ec2_conn.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(2)

    flow_logs[0]["LogFormat"].should.equal("${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}")
    flow_logs[1]["LogFormat"].should.equal("${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}")


@mock_s3
@mock_ec2
def test_flow_logs_delete():
    s3 = boto3.resource("s3", region_name="us-west-1")
    ec2_conn = boto3.client("ec2", region_name="us-west-1")

    vpc_1 = ec2_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc_2 = ec2_conn.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    response = ec2_conn.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc_1["VpcId"],vpc_2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    response.should.have.length_of(2)

    flow_logs = ec2_conn.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(2)

    ec2_conn.delete_flow_logs(FlowLogIds=[response[0]])

    flow_logs = ec2_conn.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(1)
    flow_logs[0]["FlowLogId"].should.equal(response[1])

    ec2_conn.delete_flow_logs(FlowLogIds=[response[1]])

    flow_logs = ec2_conn.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(0)


@mock_s3
@mock_ec2
def test_flow_logs_delete_many():
    s3 = boto3.resource("s3", region_name="us-west-1")
    ec2_conn = boto3.client("ec2", region_name="us-west-1")

    vpc_1 = ec2_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc_2 = ec2_conn.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    response = ec2_conn.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc_1["VpcId"],vpc_2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    response.should.have.length_of(2)

    flow_logs = ec2_conn.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(2)

    ec2_conn.delete_flow_logs(FlowLogIds=response)

    flow_logs = ec2_conn.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(0)


@mock_ec2
def test_flow_logs_delete_non_existing():
    ec2_conn = boto3.client("ec2", region_name="us-west-1")

    with assert_raises(ClientError) as ex:
        ec2_conn.delete_flow_logs(FlowLogIds=["fl-1a2b3c4d"])
    ex.exception.response["Error"]["Code"].should.equal("InvalidFlowLogId.NotFound")
    ex.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.exception.response["Error"]["Message"].should.equal(
        "These flow log ids in the input list are not found: [TotalCount: 1] fl-1a2b3c4d"
    )


@mock_ec2
def test_flow_logs_delete_non_existing_many():
    ec2_conn = boto3.client("ec2", region_name="us-west-1")

    with assert_raises(ClientError) as ex:
        ec2_conn.delete_flow_logs(FlowLogIds=["fl-1a2b3c4d","fl-2b3c4d5e"])
    ex.exception.response["Error"]["Code"].should.equal("InvalidFlowLogId.NotFound")
    ex.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.exception.response["Error"]["Message"].should.equal(
        "These flow log ids in the input list are not found: [TotalCount: 2] fl-1a2b3c4d fl-2b3c4d5e"
    )


@mock_ec2
def test_flow_logs_unsuccessful():
    s3 = boto3.resource("s3", region_name="us-west-1")
    ec2_conn = boto3.client("ec2", region_name="us-west-1")

    vpc_1 = ec2_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc_2 = ec2_conn.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    response = ec2_conn.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc_1["VpcId"],vpc_2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::non-existing-bucket",
    )
    response["FlowLogIds"].should.have.length_of(0)
    response["Unsuccessful"].should.have.length_of(2)

    error_1 = response["Unsuccessful"][0]["Error"]
    error_2 = response["Unsuccessful"][1]["Error"]

    error_1["Code"].should.equal("400")
    error_1["Message"].should.equal("LogDestination: non-existing-bucket does not exist.")
    error_2["Code"].should.equal("400")
    error_2["Message"].should.equal("LogDestination: non-existing-bucket does not exist.")


@mock_s3
@mock_ec2
def test_flow_logs_invalid_parameters():
    s3 = boto3.resource("s3", region_name="us-west-1")
    ec2_conn = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    with assert_raises(ClientError) as ex:
        ec2_conn.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
            LogDestination="arn:aws:s3:::" + bucket.name,
            MaxAggregationInterval=10,
        )
    ex.exception.response["Error"]["Code"].should.equal("InvalidParameter")
    ex.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.exception.response["Error"]["Message"].should.equal(
        "Invalid Flow Log Max Aggregation Interval"
    )

    with assert_raises(ClientError) as ex:
        ec2_conn.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
        )
    ex.exception.response["Error"]["Code"].should.equal("InvalidParameter")
    ex.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.exception.response["Error"]["Message"].should.equal(
        "LogDestination can't be empty if LogGroupName is not provided."
    )

    with assert_raises(ClientError) as ex:
        ec2_conn.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
            LogGroupName="test",
        )
    ex.exception.response["Error"]["Code"].should.equal("InvalidParameter")
    ex.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.exception.response["Error"]["Message"].should.equal(
        "LogDestination type must be cloud-watch-logs if LogGroupName is provided."
    )

    with assert_raises(ClientError) as ex:
        ec2_conn.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogGroupName="test",
        )
    ex.exception.response["Error"]["Code"].should.equal("InvalidParameter")
    ex.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.exception.response["Error"]["Message"].should.equal(
        "DeliverLogsPermissionArn can't be empty if LogDestinationType is cloud-watch-logs."
    )
