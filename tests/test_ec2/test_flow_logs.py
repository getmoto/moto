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
