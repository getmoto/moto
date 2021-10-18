import pytest

import boto3

from botocore.exceptions import ClientError
from botocore.parsers import ResponseParserError
import sure  # noqa # pylint: disable=unused-import

from moto import (
    settings,
    mock_ec2,
    mock_s3,
    mock_logs,
)
from moto.core import ACCOUNT_ID
from moto.ec2.exceptions import FilterNotImplementedError
from uuid import uuid4


@mock_s3
@mock_ec2
def test_create_flow_logs_s3():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]

    bucket_name = str(uuid4())
    bucket = s3.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "us-west-1"},
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
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
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

    flow_logs = client.describe_flow_logs(FlowLogIds=[response[0]])["FlowLogs"]
    flow_logs.should.have.length_of(1)

    flow_log = flow_logs[0]

    flow_log["FlowLogId"].should.equal(response[0])
    flow_log["DeliverLogsStatus"].should.equal("SUCCESS")
    flow_log["FlowLogStatus"].should.equal("ACTIVE")
    flow_log["ResourceId"].should.equal(vpc["VpcId"])
    flow_log["TrafficType"].should.equal("ALL")
    flow_log["LogDestinationType"].should.equal("s3")
    flow_log["LogDestination"].should.equal("arn:aws:s3:::" + bucket.name)
    flow_log["LogFormat"].should.equal(
        "${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}"
    )
    flow_log["MaxAggregationInterval"].should.equal(600)


@mock_logs
@mock_ec2
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
    ex.value.response["Error"]["Code"].should.equal("DryRunOperation")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(412)
    ex.value.response["Error"]["Message"].should.equal(
        "An error occurred (DryRunOperation) when calling the CreateFlowLogs operation: Request would have succeeded, but DryRun flag is set"
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="cloud-watch-logs",
        LogGroupName=lg_name,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"]
    response.should.have.length_of(1)

    flow_logs = client.describe_flow_logs(
        Filters=[{"Name": "resource-id", "Values": [vpc["VpcId"]]}]
    )["FlowLogs"]
    flow_logs.should.have.length_of(1)

    flow_log = flow_logs[0]

    flow_log["FlowLogId"].should.equal(response[0])
    flow_log["DeliverLogsStatus"].should.equal("SUCCESS")
    flow_log["FlowLogStatus"].should.equal("ACTIVE")
    flow_log["ResourceId"].should.equal(vpc["VpcId"])
    flow_log["TrafficType"].should.equal("ALL")
    flow_log["LogDestinationType"].should.equal("cloud-watch-logs")
    flow_log["LogGroupName"].should.equal(lg_name)
    flow_log["DeliverLogsPermissionArn"].should.equal(
        "arn:aws:iam::" + ACCOUNT_ID + ":role/test-role"
    )
    flow_log["LogFormat"].should.equal(
        "${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}"
    )
    flow_log["MaxAggregationInterval"].should.equal(600)


@mock_s3
@mock_ec2
def test_create_flow_log_create():
    s3 = boto3.resource("s3", region_name="us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")

    vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc2 = client.create_vpc(CidrBlock="10.1.0.0/16")["Vpc"]

    bucket = s3.create_bucket(
        Bucket=str(uuid4()),
        CreateBucketConfiguration={"LocationConstraint": "us-west-1",},
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc1["VpcId"], vpc2["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
        LogFormat="${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}",
    )["FlowLogIds"]
    response.should.have.length_of(2)

    flow_logs = client.describe_flow_logs(FlowLogIds=response)["FlowLogs"]
    flow_logs.should.have.length_of(2)

    flow_logs[0]["LogFormat"].should.equal(
        "${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}"
    )
    flow_logs[1]["LogFormat"].should.equal(
        "${version} ${vpc-id} ${subnet-id} ${instance-id} ${interface-id} ${account-id} ${type} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${pkt-srcaddr} ${pkt-dstaddr} ${protocol} ${bytes} ${packets} ${start} ${end} ${action} ${tcp-flags} ${log-status}"
    )


@mock_s3
@mock_ec2
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
    response.should.have.length_of(2)

    filters = [{"Name": "resource-id", "Values": [vpc1["VpcId"], vpc2["VpcId"]]}]
    flow_logs = client.describe_flow_logs(Filters=filters)["FlowLogs"]
    flow_logs.should.have.length_of(2)

    client.delete_flow_logs(FlowLogIds=[response[0]])

    flow_logs = client.describe_flow_logs(Filters=filters)["FlowLogs"]
    flow_logs.should.have.length_of(1)
    flow_logs[0]["FlowLogId"].should.equal(response[1])

    client.delete_flow_logs(FlowLogIds=[response[1]])

    flow_logs = client.describe_flow_logs(Filters=filters)["FlowLogs"]
    flow_logs.should.have.length_of(0)


@mock_s3
@mock_ec2
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
    response.should.have.length_of(2)

    all_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client)]
    for fl_id in response:
        all_ids.should.contain(fl_id)

    client.delete_flow_logs(FlowLogIds=response)

    all_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client)]
    for fl_id in response:
        all_ids.shouldnt.contain(fl_id)


@mock_ec2
def test_delete_flow_logs_non_existing():
    client = boto3.client("ec2", region_name="us-west-1")

    with pytest.raises(ClientError) as ex:
        client.delete_flow_logs(FlowLogIds=["fl-1a2b3c4d"])
    ex.value.response["Error"]["Code"].should.equal("InvalidFlowLogId.NotFound")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "These flow log ids in the input list are not found: [TotalCount: 1] fl-1a2b3c4d"
    )

    with pytest.raises(ClientError) as ex:
        client.delete_flow_logs(FlowLogIds=["fl-1a2b3c4d", "fl-2b3c4d5e"])
    ex.value.response["Error"]["Code"].should.equal("InvalidFlowLogId.NotFound")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "These flow log ids in the input list are not found: [TotalCount: 2] fl-1a2b3c4d fl-2b3c4d5e"
    )


@mock_ec2
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
    response["FlowLogIds"].should.have.length_of(0)
    response["Unsuccessful"].should.have.length_of(2)

    error1 = response["Unsuccessful"][0]["Error"]
    error2 = response["Unsuccessful"][1]["Error"]

    error1["Code"].should.equal("400")
    error1["Message"].should.equal(
        "LogDestination: non-existing-bucket does not exist."
    )
    error2["Code"].should.equal("400")
    error2["Message"].should.equal(
        "LogDestination: non-existing-bucket does not exist."
    )


@mock_s3
@mock_ec2
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
    ex.value.response["Error"]["Code"].should.equal("InvalidParameter")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "Invalid Flow Log Max Aggregation Interval"
    )

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameter")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "LogDestination can't be empty if LogGroupName is not provided."
    )

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
            LogGroupName="test",
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameter")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "LogDestination type must be cloud-watch-logs if LogGroupName is provided."
    )

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogGroupName="test",
        )
    ex.value.response["Error"]["Code"].should.equal("InvalidParameter")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "DeliverLogsPermissionArn can't be empty if LogDestinationType is cloud-watch-logs."
    )

    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogDestinationType="s3",
        LogDestination="arn:aws:s3:::" + bucket.name,
    )["FlowLogIds"]
    response.should.have.length_of(1)

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogDestinationType="s3",
            LogDestination="arn:aws:s3:::" + bucket.name,
        )
    ex.value.response["Error"]["Code"].should.equal("FlowLogAlreadyExists")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "Error. There is an existing Flow Log with the same configuration and log destination."
    )

    lg_name = str(uuid4())
    response = client.create_flow_logs(
        ResourceType="VPC",
        ResourceIds=[vpc["VpcId"]],
        TrafficType="ALL",
        LogGroupName=lg_name,
        DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
    )["FlowLogIds"]
    response.should.have.length_of(1)

    with pytest.raises(ClientError) as ex:
        client.create_flow_logs(
            ResourceType="VPC",
            ResourceIds=[vpc["VpcId"]],
            TrafficType="ALL",
            LogGroupName=lg_name,
            DeliverLogsPermissionArn="arn:aws:iam::" + ACCOUNT_ID + ":role/test-role",
        )
    ex.value.response["Error"]["Code"].should.equal("FlowLogAlreadyExists")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.value.response["Error"]["Message"].should.equal(
        "Error. There is an existing Flow Log with the same configuration and log destination."
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
    all_ids.should.contain(fl1)
    all_ids.should.contain(fl2)
    all_ids.should.contain(fl3)

    filters = [{"Name": "deliver-log-status", "Values": ["SUCCESS"]}]
    success_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client, filters)]
    success_ids.should.contain(fl1)
    success_ids.should.contain(fl2)
    success_ids.should.contain(fl3)

    filters = [{"Name": "log-destination-type", "Values": ["s3"]}]
    all_s3_logs = retrieve_all_logs(client, filters)
    s3_ids = [fl["FlowLogId"] for fl in all_s3_logs]
    s3_ids.shouldnt.contain(fl1)
    s3_ids.should.contain(fl2)
    s3_ids.shouldnt.contain(fl3)
    our_flow_log = [fl for fl in all_s3_logs if fl["FlowLogId"] == fl2][0]
    our_flow_log["ResourceId"].should.equal(vpc2["VpcId"])

    filters = [{"Name": "log-destination-type", "Values": ["cloud-watch-logs"]}]
    all_cw_logs = retrieve_all_logs(client, filters)
    cw_ids = [fl["FlowLogId"] for fl in all_cw_logs]

    fl1.should.be.within(cw_ids)
    fl2.shouldnt.be.within(cw_ids)
    fl3.should.be.within(cw_ids)

    flow_logs_resource_ids = tuple(map(lambda fl: fl["ResourceId"], all_cw_logs))
    subnet1["SubnetId"].should.be.within(flow_logs_resource_ids)
    vpc3["VpcId"].should.be.within(flow_logs_resource_ids)

    test_fl3 = next(fl for fl in all_cw_logs if fl["FlowLogId"] == fl3)
    test_fl3["DeliverLogsStatus"].should.equal("FAILED")
    test_fl3["DeliverLogsErrorMessage"].should.equal("Access error")

    filters = [{"Name": "log-destination-type", "Values": ["cloud-watch-logs", "s3"]}]
    cw_s3_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client, filters)]
    cw_s3_ids.should.contain(fl1)
    cw_s3_ids.should.contain(fl2)
    cw_s3_ids.should.contain(fl3)

    fl_by_flow_log_ids = client.describe_flow_logs(
        Filters=[{"Name": "flow-log-id", "Values": [fl1, fl3]}],
    )["FlowLogs"]
    fl_by_flow_log_ids.should.have.length_of(2)
    flow_logs_ids = tuple(map(lambda fl: fl["FlowLogId"], fl_by_flow_log_ids))
    fl1.should.be.within(flow_logs_ids)
    fl3.should.be.within(flow_logs_ids)

    flow_logs_resource_ids = tuple(map(lambda fl: fl["ResourceId"], fl_by_flow_log_ids))
    subnet1["SubnetId"].should.be.within(flow_logs_resource_ids)
    vpc3["VpcId"].should.be.within(flow_logs_resource_ids)

    fl_by_group_name = client.describe_flow_logs(
        Filters=[{"Name": "log-group-name", "Values": [lg_name]}],
    )["FlowLogs"]
    fl_by_group_name.should.have.length_of(1)
    fl_by_group_name[0]["FlowLogId"].should.equal(fl1)
    fl_by_group_name[0]["ResourceId"].should.equal(subnet1["SubnetId"])

    fl_by_group_name = client.describe_flow_logs(
        Filters=[{"Name": "log-group-name", "Values": [non_existing_group]}],
    )["FlowLogs"]
    fl_by_group_name.should.have.length_of(1)
    fl_by_group_name[0]["FlowLogId"].should.equal(fl3)
    fl_by_group_name[0]["ResourceId"].should.equal(vpc3["VpcId"])

    fl_by_resource_id = client.describe_flow_logs(
        Filters=[{"Name": "resource-id", "Values": [vpc2["VpcId"]]}],
    )["FlowLogs"]
    fl_by_resource_id.should.have.length_of(1)
    fl_by_resource_id[0]["FlowLogId"].should.equal(fl2)
    fl_by_resource_id[0]["ResourceId"].should.equal(vpc2["VpcId"])

    filters = [{"Name": "traffic-type", "Values": ["ALL"]}]
    traffic_all = retrieve_all_logs(client, filters)
    [fl["FlowLogId"] for fl in traffic_all].should.contain(fl1)
    our_flow_log = [fl for fl in traffic_all if fl["FlowLogId"] == fl1][0]
    our_flow_log["ResourceId"].should.equal(subnet1["SubnetId"])

    filters = [{"Name": "traffic-type", "Values": ["Reject"]}]
    traffic_reject = retrieve_all_logs(client, filters)
    [fl["FlowLogId"] for fl in traffic_reject].should.contain(fl3)
    our_flow_log = [fl for fl in traffic_reject if fl["FlowLogId"] == fl3][0]
    our_flow_log["ResourceId"].should.equal(vpc3["VpcId"])

    filters = [{"Name": "traffic-type", "Values": ["Accept"]}]
    traffic_accept = retrieve_all_logs(client, filters)
    [fl["FlowLogId"] for fl in traffic_accept].should.contain(fl2)
    our_flow_log = [fl for fl in traffic_accept if fl["FlowLogId"] == fl2][0]
    our_flow_log["ResourceId"].should.equal(vpc2["VpcId"])

    fl_by_tag_key = client.describe_flow_logs(
        Filters=[{"Name": "tag-key", "Values": [tag_key]}],
    )["FlowLogs"]
    fl_by_tag_key.should.have.length_of(1)
    fl_by_tag_key[0]["FlowLogId"].should.equal(fl2)
    fl_by_tag_key[0]["ResourceId"].should.equal(vpc2["VpcId"])

    fl_by_tag_key = client.describe_flow_logs(
        Filters=[{"Name": "tag-key", "Values": ["non-existing"]}],
    )["FlowLogs"]
    fl_by_tag_key.should.have.length_of(0)

    if not settings.TEST_SERVER_MODE:
        client.describe_flow_logs.when.called_with(
            Filters=[{"Name": "not-implemented-filter", "Values": ["foobar"]}],
        ).should.throw(FilterNotImplementedError)
    else:
        client.describe_flow_logs.when.called_with(
            Filters=[{"Name": "not-implemented-filter", "Values": ["foobar"]}],
        ).should.throw(ResponseParserError)


@mock_s3
@mock_ec2
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
    flow_logs.should.have.length_of(2)
    flow_logs_ids = tuple(map(lambda fl: fl["FlowLogId"], flow_logs))
    fl1.should.be.within(flow_logs_ids)
    fl3.should.be.within(flow_logs_ids)

    flow_logs_resource_ids = tuple(map(lambda fl: fl["ResourceId"], flow_logs))
    vpc1["VpcId"].should.be.within(flow_logs_resource_ids)
    vpc3["VpcId"].should.be.within(flow_logs_resource_ids)

    client.delete_flow_logs(FlowLogIds=[fl1, fl3])

    flow_logs = client.describe_flow_logs(FlowLogIds=[fl1, fl3])["FlowLogs"]
    flow_logs.should.have.length_of(0)

    all_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client)]
    all_ids.shouldnt.contain(fl1)
    all_ids.should.contain(fl2)
    all_ids.shouldnt.contain(fl3)

    flow_logs = client.delete_flow_logs(FlowLogIds=[fl2])

    all_ids = [fl["FlowLogId"] for fl in retrieve_all_logs(client)]
    all_ids.shouldnt.contain(fl1)
    all_ids.shouldnt.contain(fl2)
    all_ids.shouldnt.contain(fl3)


def retrieve_all_logs(client, filters=[]):  # pylint: disable=W0102
    resp = client.describe_flow_logs(Filters=filters)
    all_logs = resp["FlowLogs"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_flow_logs(Filters=filters, NextToken=token)
        all_logs.extend(resp["FlowLogs"])
        token = resp.get("NextToken")
    return all_logs
