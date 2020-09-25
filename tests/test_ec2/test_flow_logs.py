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

from moto import mock_cloudformation_deprecated, mock_ec2, mock_ec2_deprecated, mock_s3, mock_logs
from moto.core import ACCOUNT_ID
from moto.ec2.exceptions import FilterNotImplementedError


@mock_s3
@mock_ec2
def test_test():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet1 = client.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.0.0/18")["Subnet"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    client.create_flow_logs(
        ResourceType="Subnet",
        ResourceIds=[subnet1["SubnetId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]

    client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogGroupName="test-group",
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"]

    fls = client.describe_flow_logs()["FlowLogs"]


@mock_s3
@mock_ec2
def test_create_flow_logs():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    with assert_raises(ClientError) as ex:
        client.create_flow_logs(
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

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    response.should.have.length_of(1)

    flow_logs = client.describe_flow_logs()["FlowLogs"]
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
def test_create_flow_log_create():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"],vpc2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
        LogFormat="${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}",
    )["FlowLogIds"]
    response.should.have.length_of(2)

    flow_logs = client.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(2)

    flow_logs[0]["LogFormat"].should.equal("${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}")
    flow_logs[1]["LogFormat"].should.equal("${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}")


@mock_s3
@mock_ec2
def test_delete_flow_logs():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"],vpc2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    response.should.have.length_of(2)

    flow_logs = client.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(2)

    client.delete_flow_logs(FlowLogIds=[response[0]])

    flow_logs = client.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(1)
    flow_logs[0]["FlowLogId"].should.equal(response[1])

    client.delete_flow_logs(FlowLogIds=[response[1]])

    flow_logs = client.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(0)


@mock_s3
@mock_ec2
def test_delete_flow_logs_delete_many():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"],vpc2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    response.should.have.length_of(2)

    flow_logs = client.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(2)

    client.delete_flow_logs(FlowLogIds=response)

    flow_logs = client.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(0)


@mock_ec2
def test_delete_flow_logs_non_existing():
    client = boto3.client("ec2", region_name="us-west-1")

    with assert_raises(ClientError) as ex:
        client.delete_flow_logs(FlowLogIds=["fl-1a2b3c4d"])
    ex.exception.response["Error"]["Code"].should.equal("InvalidFlowLogId.NotFound")
    ex.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.exception.response["Error"]["Message"].should.equal(
        "These flow log ids in the input list are not found: [TotalCount: 1] fl-1a2b3c4d"
    )

    with assert_raises(ClientError) as ex:
        client.delete_flow_logs(FlowLogIds=["fl-1a2b3c4d","fl-2b3c4d5e"])
    ex.exception.response["Error"]["Code"].should.equal("InvalidFlowLogId.NotFound")
    ex.exception.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.exception.response["Error"]["Message"].should.equal(
        "These flow log ids in the input list are not found: [TotalCount: 2] fl-1a2b3c4d fl-2b3c4d5e"
    )


@mock_ec2
def test_create_flow_logs_unsuccessful():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"],vpc2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::non-existing-bucket",
    )
    response["FlowLogIds"].should.have.length_of(0)
    response["Unsuccessful"].should.have.length_of(2)

    error1 = response["Unsuccessful"][0]["Error"]
    error2 = response["Unsuccessful"][1]["Error"]

    error1["Code"].should.equal("400")
    error1["Message"].should.equal("LogDestination: non-existing-bucket does not exist.")
    error2["Code"].should.equal("400")
    error2["Message"].should.equal("LogDestination: non-existing-bucket does not exist.")


@mock_s3
@mock_ec2
def test_create_flow_logs_invalid_parameters():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket="test-flow-logs",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    with assert_raises(ClientError) as ex:
        client.create_flow_logs(
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
        client.create_flow_logs(
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
        client.create_flow_logs(
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
        client.create_flow_logs(
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


@mock_s3
@mock_ec2
@mock_logs
def test_describe_flow_logs_filtering():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    logs_client = boto3.client("logs", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]
    vpc3 = client.create_vpc(CidrBlock="10.2.0.0/16")["Vpc"]

    subnet1 = client.create_subnet(VpcId=vpc1["VpcId"], CidrBlock="10.0.0.0/18")["Subnet"]

    bucket1 = s3.create_bucket(
        Bucket="test-flow-logs-1",
        CreateBucketConfiguration={
            "LocationConstraint": "us-west-1",
        },
    )

    logs_client.create_log_group(logGroupName="test-group")

    fl1 = client.create_flow_logs(
        ResourceType="Subnet",
        ResourceIds=[subnet1["SubnetId"]],
        TrafficType="ALL",
        LogGroupName="test-group",
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"][0]

    fl2 = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc2["VpcId"]],
        TrafficType="Accept",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket1.name,
        TagSpecifications=[
            {
                "ResourceType": "vpc-flow-log",
                "Tags": [{"Key":"foo","Value":"bar"}],
            }
        ],
    )["FlowLogIds"][0]

    fl3 = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc3["VpcId"]],
        TrafficType="Reject",
        LogGroupName="non-existing-group",
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"][0]

    all_flow_logs = client.describe_flow_logs()["FlowLogs"]
    all_flow_logs.should.have.length_of(3)

    fl_by_deliver_status = client.describe_flow_logs(
        Filters=[{"Name":"deliver-log-status", "Values": ["SUCCESS"]}],
    )["FlowLogs"]
    fl_by_deliver_status.should.have.length_of(3)

    fl_by_s3_bucket = client.describe_flow_logs(
        Filters=[{"Name":"log-destination-type", "Values": ["s3"]}],
    )["FlowLogs"]
    fl_by_s3_bucket.should.have.length_of(1)
    fl_by_s3_bucket[0]["FlowLogId"].should.equal(fl2)
    fl_by_s3_bucket[0]["ResourceId"].should.equal(vpc2["VpcId"])

    fl_by_cloud_watch = client.describe_flow_logs(
        Filters=[{"Name":"log-destination-type", "Values": ["cloud-watch-logs"]}],
    )["FlowLogs"]
    fl_by_cloud_watch.should.have.length_of(2)
    fl_by_cloud_watch[0]["FlowLogId"].should.equal(fl1)
    fl_by_cloud_watch[0]["ResourceId"].should.equal(subnet1["SubnetId"])
    fl_by_cloud_watch[0]["DeliverLogsStatus"].should.equal("SUCCESS")
    fl_by_cloud_watch[1]["FlowLogId"].should.equal(fl3)
    fl_by_cloud_watch[1]["ResourceId"].should.equal(vpc3["VpcId"])
    fl_by_cloud_watch[1]["DeliverLogsStatus"].should.equal("FAILED")
    fl_by_cloud_watch[1]["DeliverLogsErrorMessage"].should.equal("Access error")

    fl_by_both = client.describe_flow_logs(
        Filters=[{"Name":"log-destination-type", "Values": ["cloud-watch-logs","s3"]}],
    )["FlowLogs"]
    fl_by_both.should.have.length_of(3)

    fl_by_flow_log_ids = client.describe_flow_logs(
        Filters=[{"Name":"flow-log-id", "Values": [fl1,fl3]}],
    )["FlowLogs"]
    fl_by_flow_log_ids.should.have.length_of(2)
    fl_by_flow_log_ids[0]["FlowLogId"].should.equal(fl1)
    fl_by_flow_log_ids[0]["ResourceId"].should.equal(subnet1["SubnetId"])
    fl_by_flow_log_ids[1]["FlowLogId"].should.equal(fl3)
    fl_by_flow_log_ids[1]["ResourceId"].should.equal(vpc3["VpcId"])

    fl_by_group_name = client.describe_flow_logs(
        Filters=[{"Name":"log-group-name", "Values": ["test-group"]}],
    )["FlowLogs"]
    fl_by_group_name.should.have.length_of(1)
    fl_by_group_name[0]["FlowLogId"].should.equal(fl1)
    fl_by_group_name[0]["ResourceId"].should.equal(subnet1["SubnetId"])

    fl_by_group_name = client.describe_flow_logs(
        Filters=[{"Name":"log-group-name", "Values": ["non-existing-group"]}],
    )["FlowLogs"]
    fl_by_group_name.should.have.length_of(1)
    fl_by_group_name[0]["FlowLogId"].should.equal(fl3)
    fl_by_group_name[0]["ResourceId"].should.equal(vpc3["VpcId"])

    fl_by_resource_id = client.describe_flow_logs(
        Filters=[{"Name":"resource-id", "Values": [vpc2["VpcId"]]}],
    )["FlowLogs"]
    fl_by_resource_id.should.have.length_of(1)
    fl_by_resource_id[0]["FlowLogId"].should.equal(fl2)
    fl_by_resource_id[0]["ResourceId"].should.equal(vpc2["VpcId"])

    fl_by_traffic_type = client.describe_flow_logs(
        Filters=[{"Name":"traffic-type", "Values": ["ALL"]}],
    )["FlowLogs"]
    fl_by_traffic_type.should.have.length_of(1)
    fl_by_traffic_type[0]["FlowLogId"].should.equal(fl1)
    fl_by_traffic_type[0]["ResourceId"].should.equal(subnet1["SubnetId"])

    fl_by_traffic_type = client.describe_flow_logs(
        Filters=[{"Name":"traffic-type", "Values": ["Reject"]}],
    )["FlowLogs"]
    fl_by_traffic_type.should.have.length_of(1)
    fl_by_traffic_type[0]["FlowLogId"].should.equal(fl3)
    fl_by_traffic_type[0]["ResourceId"].should.equal(vpc3["VpcId"])

    fl_by_traffic_type = client.describe_flow_logs(
        Filters=[{"Name":"traffic-type", "Values": ["Accept"]}],
    )["FlowLogs"]
    fl_by_traffic_type.should.have.length_of(1)
    fl_by_traffic_type[0]["FlowLogId"].should.equal(fl2)
    fl_by_traffic_type[0]["ResourceId"].should.equal(vpc2["VpcId"])

    fl_by_tag_key = client.describe_flow_logs(
        Filters=[{"Name":"tag-key", "Values": ["foo"]}],
    )["FlowLogs"]
    fl_by_tag_key.should.have.length_of(1)
    fl_by_tag_key[0]["FlowLogId"].should.equal(fl2)
    fl_by_tag_key[0]["ResourceId"].should.equal(vpc2["VpcId"])

    with assert_raises(FilterNotImplementedError):
        client.describe_flow_logs(
            Filters=[{"Name": "not-implemented-filter", "Values": ["foobar"]}],
        )


@mock_s3
@mock_ec2
def test_flow_logs_by_ids():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]
    vpc3 = client.create_vpc(CidrBlock="10.2.0.0/16")["Vpc"]

    fl1 = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"]],
        TrafficType="Reject",
        LogGroupName="test-group-1",
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role-1",
    )["FlowLogIds"][0]

    fl2 = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc2["VpcId"]],
        TrafficType="Reject",
        LogGroupName="test-group-3",
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role-3",
    )["FlowLogIds"][0]

    fl3 = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc3["VpcId"]],
        TrafficType="Reject",
        LogGroupName="test-group-3",
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role-3",
    )["FlowLogIds"][0]

    flow_logs = client.describe_flow_logs(
        FlowLogIds=[fl1,fl3],
    )["FlowLogs"]
    flow_logs.should.have.length_of(2)
    flow_logs[0]["FlowLogId"].should.equal(fl1)
    flow_logs[0]["ResourceId"].should.equal(vpc1["VpcId"])
    flow_logs[1]["FlowLogId"].should.equal(fl3)
    flow_logs[1]["ResourceId"].should.equal(vpc3["VpcId"])

    client.delete_flow_logs(
        FlowLogIds=[fl1,fl3],
    )

    flow_logs = client.describe_flow_logs(
        FlowLogIds=[fl1,fl3],
    )["FlowLogs"]
    flow_logs.should.have.length_of(0)

    flow_logs = client.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(1)
    flow_logs[0]["FlowLogId"].should.equal(fl2)
    flow_logs[0]["ResourceId"].should.equal(vpc2["VpcId"])

    flow_logs = client.delete_flow_logs(
        FlowLogIds=[fl2],
    )
    flow_logs = client.describe_flow_logs()["FlowLogs"]
    flow_logs.should.have.length_of(0)
