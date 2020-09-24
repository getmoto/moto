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
def test_flow_log():
    s3 = boto3.resource("s3", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")

    ec2_client = boto3.client("ec2", region_name="us-east-1")

    vpc1 = ec2.create_vpc(CidrBlock="192.168.0.0/24")
    vpc2 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc1.reload()
    vpc2.reload()

    b = s3.create_bucket(Bucket="test-flow-logs")

    # Invalid MaxAggregationInterval
    #resp = ec2_client.create_flow_logs(ResourceType="VPC",ResourceIds=[vpc.id],TrafficType="ALL",LogGroupName="test",
    #                        DeliverLogsPermissionArn="arn:aws:iam::003740049406:role/test",MaxAggregationInterval="700")

    # Missing LogDestination for s3
    #resp = ec2_client.create_flow_logs(ResourceType="VPC",ResourceIds=[vpc.id],TrafficType="ALL",LogDestinationType="s3")

    # Wrong LogDestinationType when LogGroupName is provided
    #resp = ec2_client.create_flow_logs(ResourceType="VPC",ResourceIds=[vpc.id],TrafficType="ALL",LogDestinationType="s3",LogGroupName="test")

    # Missing DeliverLogsPermissionArn
    #resp = ec2_client.create_flow_logs(ResourceType="VPC",ResourceIds=[vpc.id],TrafficType="ALL",LogGroupName="test")

    #resp = ec2_client.create_flow_logs(ResourceType="VPC",ResourceIds=[vpc.id],TrafficType="ALL",LogDestinationType="s3",LogDestination="arn:aws:s3:::" + vpc.id + "-flow-logs")

    flow_logs = ec2_client.create_flow_logs(ResourceType="VPC",ResourceIds=[vpc1.id,vpc2.id],TrafficType="ALL",LogDestinationType="s3",LogDestination="arn:aws:s3:::test-flow-logs")
    #flow_log_2 = ec2_client.create_flow_logs(ResourceType="VPC",ResourceIds=[vpc.id],TrafficType="REJECT",LogGroupName="test",
    #                       DeliverLogsPermissionArn="arn:aws:iam::0123456789101:role/test",MaxAggregationInterval="600")

    #fl_id_1 = flow_log_1['FlowLogIds'][0]

    ec2_client.describe_flow_logs()
    ec2_client.delete_flow_logs(FlowLogIds=[flow_logs['FlowLogIds'][1]])
    ec2_client.describe_flow_logs()
