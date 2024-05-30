from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
@pytest.mark.parametrize(
    "region,partition", [("us-west-2", "aws"), ("cn-north-1", "aws-cn")]
)
def test_create_flow_logs_s3(region, partition):
    s3 = boto3.resource("s3", region_name=region)
    client = boto3.client("ec2", region_name=region)

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket_name = str(uuid4())
    bucket = s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": region},
    )

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
            LogDestination="arn:aws:s3:::" + bucket.name,
            DryRun=True,
        )
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateFlowLogs operation: Request would have succeeded, but DryRun flag is set"
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    assert len(response) == 1

    flow_logs = client.describe_flow_logs(FlowLogIds=[response[0]])["FlowLogs"]
    assert len(flow_logs) == 1

    flow_log = flow_logs[0]

    assert flow_log["FlowLogId"] == response[0]
    assert flow_log["DeliverLogsStatus"] == "SUCCESS"
    assert flow_log["FlowLogStatus"] == "ACTIVE"
    assert flow_log["ResourceId"] == vpc["VpcId"]
    assert flow_log["TrafficType"] == "ALL"
    assert flow_log["LogDestinationType"] == "s3"
    assert flow_log["LogDestination"] == "arn:aws:s3:::" + bucket.name
    assert (
        flow_log["LogFormat"]
        == "${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}"
    )
    assert flow_log["MaxAggregationInterval"] == 600


@mock_aws
def test_create_multiple_flow_logs_s3():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket_name_1 = str(uuid4())
    bucket_1 = s3.create_bucket(
        Bucket=bucket_name_1,
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )
    bucket_name_2 = str(uuid4())
    bucket_2 = s3.create_bucket(
        Bucket=bucket_name_2,
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket_1.name,
    )["FlowLogIds"]
    assert len(response) == 1

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket_2.name,
    )["FlowLogIds"]
    assert len(response) == 1

    flow_logs = client.describe_flow_logs(
        Filters=[{"Name": "resource-id", "Values": [vpc["VpcId"]]}]
    )["FlowLogs"]
    assert len(flow_logs) == 2

    flow_log_1 = flow_logs[0]
    flow_log_2 = flow_logs[1]

    assert flow_log_1["ResourceId"] == flow_log_2["ResourceId"]
    assert flow_log_1["FlowLogId"] != flow_log_2["FlowLogId"]
    assert flow_log_1["LogDestination"] != flow_log_2["LogDestination"]


@mock_aws
def test_create_flow_logs_s3__bucket_in_different_partition():
    s3 = boto3.resource("s3", region_name="cn-north-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket_name = str(uuid4())
    bucket = s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "cn-north-1"},
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    assert len(response) == 1

    flow_logs = client.describe_flow_logs(FlowLogIds=[response[0]])["FlowLogs"]
    assert len(flow_logs) == 1


@mock_aws
def test_create_flow_logs_cloud_watch():
    client = boto3.client("ec2", region_name="us-west-1")
    logs_client = boto3.client("logs", region_name="us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    lg_name = str(uuid4())
    logs_client.create_log_group(logGroupName=lg_name)

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="cloud-watch-logs",
            LogGroupName=lg_name,
            DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
            DryRun=True,
        )
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateFlowLogs operation: Request would have succeeded, but DryRun flag is set"
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="cloud-watch-logs",
        LogGroupName=lg_name,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"]
    assert len(response) == 1

    flow_logs = client.describe_flow_logs(
        Filters=[{"Name": "resource-id", "Values": [vpc["VpcId"]]}]
    )["FlowLogs"]
    assert len(flow_logs) == 1

    flow_log = flow_logs[0]

    assert flow_log["FlowLogId"] == response[0]
    assert flow_log["DeliverLogsStatus"] == "SUCCESS"
    assert flow_log["FlowLogStatus"] == "ACTIVE"
    assert flow_log["ResourceId"] == vpc["VpcId"]
    assert flow_log["TrafficType"] == "ALL"
    assert flow_log["LogDestinationType"] == "cloud-watch-logs"
    assert flow_log["LogGroupName"] == lg_name
    assert (
        flow_log["DeliverLogsPermissionArn"]
        == "arn:aws:iam::" + ACCOUNT_ID + ":role/test-role"
    )
    assert (
        flow_log["LogFormat"]
        == "${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}"
    )
    assert flow_log["MaxAggregationInterval"] == 600


@mock_aws
def test_create_multiple_flow_logs_cloud_watch():
    client = boto3.client("ec2", region_name="us-west-1")
    logs_client = boto3.client("logs", region_name="us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    lg_name_1 = str(uuid4())
    lg_name_2 = str(uuid4())
    logs_client.create_log_group(logGroupName=lg_name_1)
    logs_client.create_log_group(logGroupName=lg_name_2)

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="cloud-watch-logs",
        LogGroupName=lg_name_1,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"]
    assert len(response) == 1

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="cloud-watch-logs",
        LogGroupName=lg_name_2,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"]
    assert len(response) == 1

    flow_logs = client.describe_flow_logs(
        Filters=[{"Name": "resource-id", "Values": [vpc["VpcId"]]}]
    )["FlowLogs"]
    assert len(flow_logs) == 2

    flow_log_1 = flow_logs[0]
    flow_log_2 = flow_logs[1]

    assert flow_log_1["ResourceId"] == flow_log_2["ResourceId"]
    assert flow_log_1["FlowLogId"] != flow_log_2["FlowLogId"]
    assert flow_log_1["LogGroupName"] != flow_log_2["LogGroupName"]


@mock_aws
def test_create_flow_log_create():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket=str(uuid4()),
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"], vpc2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
        LogFormat="${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}",
    )["FlowLogIds"]
    assert len(response) == 2

    flow_logs = client.describe_flow_logs(FlowLogIds=response)["FlowLogs"]
    assert len(flow_logs) == 2

    assert (
        flow_logs[0]["LogFormat"]
        == "${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}"
    )
    assert (
        flow_logs[1]["LogFormat"]
        == "${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}"
    )


@mock_aws
def test_delete_flow_logs():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket=str(uuid4()),
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"], vpc2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    assert len(response) == 2

    filters = [{"Name": "resource-id", "Values": [vpc1["VpcId"], vpc2["VpcId"]]}]
    flow_logs = client.describe_flow_logs(Filters=filters)["FlowLogs"]
    assert len(flow_logs) == 2

    client.delete_flow_logs(FlowLogIds=[response[0]])

    flow_logs = client.describe_flow_logs(Filters=filters)["FlowLogs"]
    assert len(flow_logs) == 1
    assert flow_logs[0]["FlowLogId"] == response[1]

    client.delete_flow_logs(FlowLogIds=[response[1]])

    flow_logs = client.describe_flow_logs(Filters=filters)["FlowLogs"]
    assert len(flow_logs) == 0


@mock_aws
def test_delete_flow_logs_delete_many():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket=str(uuid4()),
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"], vpc2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    assert len(response) == 2

    all_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client)]
    for fl_id in response:
        assert fl_id in all_ids

    client.delete_flow_logs(FlowLogIds=response)

    all_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client)]
    for fl_id in response:
        assert fl_id not in all_ids


@mock_aws
def test_delete_flow_logs_non_existing():
    client = boto3.client("ec2", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.delete_flow_logs(FlowLogIds=["fl-1a2b3c4d"])
    assert ex.value.response["Error"]["Code"] == "InvalidFlowLogId.NotFound"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "These flow log ids in the input list are not found: [TotalCount: 1] fl-1a2b3c4d"
    )

    with pytest.raises(ClientError) as ex:
        client.delete_flow_logs(FlowLogIds=["fl-1a2b3c4d", "fl-2b3c4d5e"])
    assert ex.value.response["Error"]["Code"] == "InvalidFlowLogId.NotFound"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "These flow log ids in the input list are not found: [TotalCount: 2] fl-1a2b3c4d fl-2b3c4d5e"
    )


@mock_aws
def test_create_flow_logs_unsuccessful():
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"], vpc2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::non-existing-bucket",
    )
    assert len(response["FlowLogIds"]) == 0
    assert len(response["Unsuccessful"]) == 2

    error1 = response["Unsuccessful"][0]["Error"]
    error2 = response["Unsuccessful"][1]["Error"]

    assert error1["Code"] == "400"
    assert error1["Message"] == "LogDestination: non-existing-bucket does not exist."
    assert error2["Code"] == "400"
    assert error2["Message"] == "LogDestination: non-existing-bucket does not exist."


@mock_aws
def test_create_flow_logs_invalid_parameters():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket=str(uuid4()),
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
            LogDestination="arn:aws:s3:::" + bucket.name,
            MaxAggregationInterval=10,
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameter"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "Invalid Flow Log Max Aggregation Interval"
    )

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameter"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "LogDestination can't be empty if LogGroupName is not provided."
    )

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
            LogGroupName="test",
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameter"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "LogDestination type must be cloud-watch-logs if LogGroupName is provided."
    )

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogGroupName="test",
        )
    assert ex.value.response["Error"]["Code"] == "InvalidParameter"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "DeliverLogsPermissionArn can't be empty if LogDestinationType is cloud-watch-logs."
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    assert len(response) == 1

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
            LogDestination="arn:aws:s3:::" + bucket.name,
        )
    assert ex.value.response["Error"]["Code"] == "FlowLogAlreadyExists"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "Error. There is an existing Flow Log with the same configuration and log destination."
    )

    lg_name = str(uuid4())
    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogGroupName=lg_name,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"]
    assert len(response) == 1

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogGroupName=lg_name,
            DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
        )
    assert ex.value.response["Error"]["Code"] == "FlowLogAlreadyExists"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert (
        ex.value.response["Error"]["Message"]
        == "Error. There is an existing Flow Log with the same configuration and log destination."
    )


@mock_aws
def test_describe_flow_logs_filtering():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    logs_client = boto3.client("logs", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]
    vpc3 = client.create_vpc(CidrBlock="10.2.0.0/16")["Vpc"]

    subnet1 = client.create_subnet(VpcId=vpc1["VpcId"], CidrBlock="10.0.0.0/18")[
        "Subnet"
    ]

    bucket1 = s3.create_bucket(
        Bucket=str(uuid4()),
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
    )

    lg_name = str(uuid4())
    logs_client.create_log_group(logGroupName=lg_name)

    fl1 = client.create_flow_logs(
        ResourceType="Subnet",
        ResourceIds=[subnet1["SubnetId"]],
        TrafficType="ALL",
        LogGroupName=lg_name,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"][0]

    tag_key = str(uuid4())[0:6]
    fl2 = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc2["VpcId"]],
        TrafficType="Accept",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket1.name,
        TagSpecifications=[
            {"ResourceType": "vpc-flow-log", "Tags": [{"Key": tag_key, "Value": "bar"}]}
        ],
    )["FlowLogIds"][0]

    non_existing_group = str(uuid4())
    fl3 = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc3["VpcId"]],
        TrafficType="Reject",
        LogGroupName=non_existing_group,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"][0]

    all_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client)]
    assert fl1 in all_ids
    assert fl2 in all_ids
    assert fl3 in all_ids

    filters = [{"Name": "deliver-log-status", "Values": ["SUCCESS"]}]
    success_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client, filters)]
    assert fl1 in success_ids
    assert fl2 in success_ids
    assert fl3 in success_ids

    filters = [{"Name": "log-destination-type", "Values": ["s3"]}]
    all_s3_logs = retrieve_all_logs(client, filters)
    s3_ids = [fl["FlowLogId"] for fl in all_s3_logs]
    assert fl1 not in s3_ids
    assert fl2 in s3_ids
    assert fl3 not in s3_ids
    our_flow_log = [fl for fl in all_s3_logs if fl["FlowLogId"] == fl2][0]
    assert our_flow_log["ResourceId"] == vpc2["VpcId"]

    filters = [{"Name": "log-destination-type", "Values": ["cloud-watch-logs"]}]
    all_cw_logs = retrieve_all_logs(client, filters)
    cw_ids = [fl["FlowLogId"] for fl in all_cw_logs]

    assert fl1 in cw_ids
    assert fl2 not in cw_ids
    assert fl3 in cw_ids

    flow_logs_resource_ids = tuple(map(lambda fl: fl["ResourceId"], all_cw_logs))
    assert subnet1["SubnetId"] in flow_logs_resource_ids
    assert vpc3["VpcId"] in flow_logs_resource_ids

    test_fl3 = next(fl for fl in all_cw_logs if fl["FlowLogId"] == fl3)
    assert test_fl3["DeliverLogsStatus"] == "FAILED"
    assert test_fl3["DeliverLogsErrorMessage"] == "Access error"

    filters = [{"Name": "log-destination-type", "Values": ["cloud-watch-logs", "s3"]}]
    cw_s3_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client, filters)]
    assert fl1 in cw_s3_ids
    assert fl2 in cw_s3_ids
    assert fl3 in cw_s3_ids

    fl_by_flow_log_ids = client.describe_flow_logs(
        Filters=[{"Name": "flow-log-id", "Values": [fl1, fl3]}]
    )["FlowLogs"]
    assert len(fl_by_flow_log_ids) == 2
    flow_logs_ids = tuple(map(lambda fl: fl["FlowLogId"], fl_by_flow_log_ids))
    assert fl1 in flow_logs_ids
    assert fl3 in flow_logs_ids

    flow_logs_resource_ids = tuple(map(lambda fl: fl["ResourceId"], fl_by_flow_log_ids))
    assert subnet1["SubnetId"] in flow_logs_resource_ids
    assert vpc3["VpcId"] in flow_logs_resource_ids

    fl_by_group_name = client.describe_flow_logs(
        Filters=[{"Name": "log-group-name", "Values": [lg_name]}]
    )["FlowLogs"]
    assert len(fl_by_group_name) == 1
    assert fl_by_group_name[0]["FlowLogId"] == fl1
    assert fl_by_group_name[0]["ResourceId"] == subnet1["SubnetId"]

    fl_by_group_name = client.describe_flow_logs(
        Filters=[{"Name": "log-group-name", "Values": [non_existing_group]}]
    )["FlowLogs"]
    assert len(fl_by_group_name) == 1
    assert fl_by_group_name[0]["FlowLogId"] == fl3
    assert fl_by_group_name[0]["ResourceId"] == vpc3["VpcId"]

    fl_by_resource_id = client.describe_flow_logs(
        Filters=[{"Name": "resource-id", "Values": [vpc2["VpcId"]]}]
    )["FlowLogs"]
    assert len(fl_by_resource_id) == 1
    assert fl_by_resource_id[0]["FlowLogId"] == fl2
    assert fl_by_resource_id[0]["ResourceId"] == vpc2["VpcId"]

    filters = [{"Name": "traffic-type", "Values": ["ALL"]}]
    traffic_all = retrieve_all_logs(client, filters)
    assert fl1 in [fl["FlowLogId"] for fl in traffic_all]
    our_flow_log = [fl for fl in traffic_all if fl["FlowLogId"] == fl1][0]
    assert our_flow_log["ResourceId"] == subnet1["SubnetId"]

    filters = [{"Name": "traffic-type", "Values": ["Reject"]}]
    traffic_reject = retrieve_all_logs(client, filters)
    assert fl3 in [fl["FlowLogId"] for fl in traffic_reject]
    our_flow_log = [fl for fl in traffic_reject if fl["FlowLogId"] == fl3][0]
    assert our_flow_log["ResourceId"] == vpc3["VpcId"]

    filters = [{"Name": "traffic-type", "Values": ["Accept"]}]
    traffic_accept = retrieve_all_logs(client, filters)
    assert fl2 in [fl["FlowLogId"] for fl in traffic_accept]
    our_flow_log = [fl for fl in traffic_accept if fl["FlowLogId"] == fl2][0]
    assert our_flow_log["ResourceId"] == vpc2["VpcId"]

    fl_by_tag_key = client.describe_flow_logs(
        Filters=[{"Name": "tag-key", "Values": [tag_key]}]
    )["FlowLogs"]
    assert len(fl_by_tag_key) == 1
    assert fl_by_tag_key[0]["FlowLogId"] == fl2
    assert fl_by_tag_key[0]["ResourceId"] == vpc2["VpcId"]

    fl_by_tag_key = client.describe_flow_logs(
        Filters=[{"Name": "tag-key", "Values": ["non-existing"]}]
    )["FlowLogs"]
    assert len(fl_by_tag_key) == 0

    # NotYetImplemented
    with pytest.raises(Exception):
        client.describe_flow_logs(Filters=[{"Name": "unknown", "Values": ["foobar"]}])


@mock_aws
def test_flow_logs_by_ids():
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]
    vpc3 = client.create_vpc(CidrBlock="10.2.0.0/16")["Vpc"]

    lg1_name = str(uuid4())
    fl1 = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"]],
        TrafficType="Reject",
        LogGroupName=lg1_name,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role-1",
    )["FlowLogIds"][0]

    lg3_name = str(uuid4())
    fl2 = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc2["VpcId"]],
        TrafficType="Reject",
        LogGroupName=lg3_name,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role-3",
    )["FlowLogIds"][0]

    fl3 = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc3["VpcId"]],
        TrafficType="Reject",
        LogGroupName=lg3_name,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role-3",
    )["FlowLogIds"][0]

    flow_logs = client.describe_flow_logs(FlowLogIds=[fl1, fl3])["FlowLogs"]
    assert len(flow_logs) == 2
    flow_logs_ids = tuple(map(lambda fl: fl["FlowLogId"], flow_logs))
    assert fl1 in flow_logs_ids
    assert fl3 in flow_logs_ids

    flow_logs_resource_ids = tuple(map(lambda fl: fl["ResourceId"], flow_logs))
    assert vpc1["VpcId"] in flow_logs_resource_ids
    assert vpc3["VpcId"] in flow_logs_resource_ids

    client.delete_flow_logs(FlowLogIds=[fl1, fl3])

    flow_logs = client.describe_flow_logs(FlowLogIds=[fl1, fl3])["FlowLogs"]
    assert len(flow_logs) == 0

    all_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client)]
    assert fl1 not in all_ids
    assert fl2 in all_ids
    assert fl3 not in all_ids

    flow_logs = client.delete_flow_logs(FlowLogIds=[fl2])

    all_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client)]
    assert fl1 not in all_ids
    assert fl2 not in all_ids
    assert fl3 not in all_ids


def retrieve_all_logs(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_flow_logs(Filters=filters)
    all_logs = resp["FlowLogs"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_flow_logs(Filters=filters, NextToken=token)
        all_logs.extend(resp["FlowLogs"])
        token = resp.get("NextToken")
    return all_logs
