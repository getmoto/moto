import boto3
import pytest

from moto import mock_aws

REGION = "us-east-1"
NAMESPACE = "sagemaker"
RESOURCE_ID = "endpoint/MyEndPoint/variant/MyVariant"
DIMENSION = "sagemaker:variant:DesiredInstanceCount"


def _register_target(client, **kwargs) -> str:
    return client.register_scalable_target(
        ServiceNamespace=NAMESPACE,
        ResourceId=RESOURCE_ID,
        ScalableDimension=DIMENSION,
        MinCapacity=1,
        MaxCapacity=8,
        **kwargs,
    )["ScalableTargetARN"]


@mock_aws
def test_register_scalable_target_with_tags():
    client = boto3.client("application-autoscaling", region_name=REGION)
    arn = _register_target(client, Tags={"env": "test", "team": "data"})

    tags = client.list_tags_for_resource(ResourceARN=arn)["Tags"]
    assert tags == {"env": "test", "team": "data"}


@mock_aws
def test_list_tags_for_resource_without_tags():
    client = boto3.client("application-autoscaling", region_name=REGION)
    arn = _register_target(client)

    assert client.list_tags_for_resource(ResourceARN=arn)["Tags"] == {}


@mock_aws
def test_tag_resource_adds_and_overwrites_tags():
    client = boto3.client("application-autoscaling", region_name=REGION)
    arn = _register_target(client, Tags={"env": "test"})

    client.tag_resource(ResourceARN=arn, Tags={"env": "prod", "owner": "me"})

    tags = client.list_tags_for_resource(ResourceARN=arn)["Tags"]
    assert tags == {"env": "prod", "owner": "me"}


@mock_aws
def test_untag_resource():
    client = boto3.client("application-autoscaling", region_name=REGION)
    arn = _register_target(client, Tags={"env": "test", "owner": "me"})

    client.untag_resource(ResourceARN=arn, TagKeys=["env", "unknown"])

    assert client.list_tags_for_resource(ResourceARN=arn)["Tags"] == {"owner": "me"}


@mock_aws
def test_tag_resource_too_many_tags():
    client = boto3.client("application-autoscaling", region_name=REGION)
    arn = _register_target(client, Tags={f"key{i}": "v" for i in range(45)})

    with pytest.raises(client.exceptions.TooManyTagsException):
        client.tag_resource(ResourceARN=arn, Tags={f"new{i}": "v" for i in range(6)})
    assert len(client.list_tags_for_resource(ResourceARN=arn)["Tags"]) == 45


@mock_aws
@pytest.mark.parametrize(
    "operation,kwargs",
    [
        ("list_tags_for_resource", {}),
        ("tag_resource", {"Tags": {"env": "test"}}),
        ("untag_resource", {"TagKeys": ["env"]}),
    ],
)
def test_tagging_unknown_resource(operation, kwargs):
    client = boto3.client("application-autoscaling", region_name=REGION)
    arn = f"arn:aws:application-autoscaling:{REGION}:123456789012:scalable-target/0123456789abcdef0123456789abcdef0123"

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        getattr(client, operation)(ResourceARN=arn, **kwargs)


@mock_aws
def test_deregister_scalable_target_removes_tags():
    client = boto3.client("application-autoscaling", region_name=REGION)
    arn = _register_target(client, Tags={"env": "test"})
    client.deregister_scalable_target(
        ServiceNamespace=NAMESPACE, ResourceId=RESOURCE_ID, ScalableDimension=DIMENSION
    )

    # registering the same target again creates a new resource without the old tags
    new_arn = _register_target(client)
    assert new_arn != arn
    assert client.list_tags_for_resource(ResourceARN=new_arn)["Tags"] == {}


@mock_aws
def test_scalable_targets_in_resource_groups_tagging_api():
    client = boto3.client("application-autoscaling", region_name=REGION)
    arn = _register_target(client, Tags={"env": "test"})
    rgta = boto3.client("resourcegroupstaggingapi", region_name=REGION)

    resources = rgta.get_resources(ResourceTypeFilters=["application-autoscaling"])[
        "ResourceTagMappingList"
    ]
    assert resources == [
        {"ResourceARN": arn, "Tags": [{"Key": "env", "Value": "test"}]}
    ]

    rgta.tag_resources(ResourceARNList=[arn], Tags={"team": "data"})
    rgta.untag_resources(ResourceARNList=[arn], TagKeys=["env"])
    assert client.list_tags_for_resource(ResourceARN=arn)["Tags"] == {"team": "data"}
