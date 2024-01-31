import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


# RegisterActivityType endpoint
@mock_aws
def test_register_activity_type_boto3():
    client = boto3.client("swf", region_name="us-west-2")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_activity_type(
        domain="test-domain", name="test-activity", version="v1.0"
    )

    types = client.list_activity_types(
        domain="test-domain", registrationStatus="REGISTERED"
    )["typeInfos"]
    assert len(types) == 1
    actype = types[0]
    assert actype["activityType"]["name"] == "test-activity"
    assert actype["activityType"]["version"] == "v1.0"


@mock_aws
def test_register_already_existing_activity_type_boto3():
    client = boto3.client("swf", region_name="us-west-2")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_activity_type(
        domain="test-domain", name="test-activity", version="v1.0"
    )

    with pytest.raises(ClientError) as ex:
        client.register_activity_type(
            domain="test-domain", name="test-activity", version="v1.0"
        )
    assert ex.value.response["Error"]["Code"] == "TypeAlreadyExistsFault"
    assert ex.value.response["Error"]["Message"] == (
        "ActivityType=[name=test-activity, version=v1.0]"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


# ListActivityTypes endpoint


# ListActivityTypes endpoint
@mock_aws
def test_list_activity_types_boto3():
    client = boto3.client("swf", region_name="us-west-2")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_activity_type(
        domain="test-domain", name="b-test-activity", version="v1.0"
    )
    client.register_activity_type(
        domain="test-domain", name="a-test-activity", version="v1.0"
    )
    client.register_activity_type(
        domain="test-domain", name="c-test-activity", version="v1.0"
    )

    types = client.list_activity_types(
        domain="test-domain", registrationStatus="REGISTERED"
    )
    names = [
        activity_type["activityType"]["name"] for activity_type in types["typeInfos"]
    ]
    assert names == ["a-test-activity", "b-test-activity", "c-test-activity"]


@mock_aws
def test_list_activity_types_reverse_order_boto3():
    client = boto3.client("swf", region_name="us-west-2")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_activity_type(
        domain="test-domain", name="b-test-activity", version="v1.0"
    )
    client.register_activity_type(
        domain="test-domain", name="a-test-activity", version="v1.0"
    )
    client.register_activity_type(
        domain="test-domain", name="c-test-activity", version="v1.0"
    )

    types = client.list_activity_types(
        domain="test-domain", registrationStatus="REGISTERED", reverseOrder=True
    )

    names = [
        activity_type["activityType"]["name"] for activity_type in types["typeInfos"]
    ]
    assert names == ["c-test-activity", "b-test-activity", "a-test-activity"]


# DeprecateActivityType endpoint
@mock_aws
def test_deprecate_activity_type_boto3():
    client = boto3.client("swf", region_name="us-west-2")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_activity_type(
        domain="test-domain", name="test-activity", version="v1.0"
    )
    client.deprecate_activity_type(
        domain="test-domain", activityType={"name": "test-activity", "version": "v1.0"}
    )

    types = client.list_activity_types(
        domain="test-domain", registrationStatus="DEPRECATED"
    )
    assert len(types["typeInfos"]) == 1
    actype = types["typeInfos"][0]
    assert actype["activityType"]["name"] == "test-activity"
    assert actype["activityType"]["version"] == "v1.0"


@mock_aws
def test_deprecate_already_deprecated_activity_type_boto3():
    client = boto3.client("swf", region_name="us-west-2")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_activity_type(
        domain="test-domain", name="test-activity", version="v1.0"
    )
    client.deprecate_activity_type(
        domain="test-domain", activityType={"name": "test-activity", "version": "v1.0"}
    )

    with pytest.raises(ClientError) as ex:
        client.deprecate_activity_type(
            domain="test-domain",
            activityType={"name": "test-activity", "version": "v1.0"},
        )
    assert ex.value.response["Error"]["Code"] == "TypeDeprecatedFault"
    assert ex.value.response["Error"]["Message"] == (
        "ActivityType=[name=test-activity, version=v1.0]"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_deprecate_non_existent_activity_type_boto3():
    client = boto3.client("swf", region_name="us-west-2")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    with pytest.raises(ClientError) as ex:
        client.deprecate_activity_type(
            domain="test-domain",
            activityType={"name": "test-activity", "version": "v1.0"},
        )
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown type: ActivityType=[name=test-activity, version=v1.0]"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


# DeprecateActivityType endpoint
@mock_aws
def test_undeprecate_activity_type():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_activity_type(
        domain="test-domain", name="test-activity", version="v1.0"
    )
    client.deprecate_activity_type(
        domain="test-domain", activityType={"name": "test-activity", "version": "v1.0"}
    )
    client.undeprecate_activity_type(
        domain="test-domain", activityType={"name": "test-activity", "version": "v1.0"}
    )

    resp = client.describe_activity_type(
        domain="test-domain", activityType={"name": "test-activity", "version": "v1.0"}
    )
    assert resp["typeInfo"]["status"] == "REGISTERED"


@mock_aws
def test_undeprecate_already_undeprecated_activity_type():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_activity_type(
        domain="test-domain", name="test-activity", version="v1.0"
    )
    client.deprecate_activity_type(
        domain="test-domain", activityType={"name": "test-activity", "version": "v1.0"}
    )
    client.undeprecate_activity_type(
        domain="test-domain", activityType={"name": "test-activity", "version": "v1.0"}
    )

    with pytest.raises(ClientError):
        client.undeprecate_activity_type(
            domain="test-domain",
            activityType={"name": "test-activity", "version": "v1.0"},
        )


@mock_aws
def test_undeprecate_never_deprecated_activity_type():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_activity_type(
        domain="test-domain", name="test-activity", version="v1.0"
    )

    with pytest.raises(ClientError):
        client.undeprecate_activity_type(
            domain="test-domain",
            activityType={"name": "test-activity", "version": "v1.0"},
        )


@mock_aws
def test_undeprecate_non_existent_activity_type():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    with pytest.raises(ClientError):
        client.undeprecate_activity_type(
            domain="test-domain",
            activityType={"name": "test-activity", "version": "v1.0"},
        )


# DescribeActivityType endpoint
@mock_aws
def test_describe_activity_type_boto3():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )
    client.register_activity_type(
        domain="test-domain",
        name="test-activity",
        version="v1.0",
        defaultTaskList={"name": "foo"},
        defaultTaskHeartbeatTimeout="32",
    )

    actype = client.describe_activity_type(
        domain="test-domain", activityType={"name": "test-activity", "version": "v1.0"}
    )
    assert actype["configuration"]["defaultTaskList"]["name"] == "foo"
    infos = actype["typeInfo"]
    assert infos["activityType"]["name"] == "test-activity"
    assert infos["activityType"]["version"] == "v1.0"
    assert infos["status"] == "REGISTERED"


@mock_aws
def test_describe_non_existent_activity_type_boto3():
    client = boto3.client("swf", region_name="us-east-1")
    client.register_domain(
        name="test-domain", workflowExecutionRetentionPeriodInDays="60"
    )

    with pytest.raises(ClientError) as ex:
        client.describe_activity_type(
            domain="test-domain",
            activityType={"name": "test-activity", "version": "v1.0"},
        )
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown type: ActivityType=[name=test-activity, version=v1.0]"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
