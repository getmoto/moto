import boto3

from moto import mock_ecs
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_ecs
def test_create_capacity_provider():
    client = boto3.client("ecs", region_name="us-west-1")
    resp = client.create_capacity_provider(
        name="my_provider",
        autoScalingGroupProvider={
            "autoScalingGroupArn": "asg:arn",
            "managedScaling": {
                "status": "ENABLED",
                "targetCapacity": 5,
                "maximumScalingStepSize": 2,
            },
            "managedTerminationProtection": "DISABLED",
        },
    )

    provider = resp["capacityProvider"]
    assert "capacityProviderArn" in provider
    assert provider["name"] == "my_provider"
    assert provider["status"] == "ACTIVE"
    assert provider["autoScalingGroupProvider"] == {
        "autoScalingGroupArn": "asg:arn",
        "managedScaling": {
            "instanceWarmupPeriod": 300,
            "status": "ENABLED",
            "targetCapacity": 5,
            "minimumScalingStepSize": 1,
            "maximumScalingStepSize": 2,
        },
        "managedTerminationProtection": "DISABLED",
    }


@mock_ecs
def test_create_capacity_provider_with_tags():
    client = boto3.client("ecs", region_name="us-west-1")
    resp = client.create_capacity_provider(
        name="my_provider",
        autoScalingGroupProvider={"autoScalingGroupArn": "asg:arn"},
        tags=[{"key": "k1", "value": "v1"}],
    )

    provider = resp["capacityProvider"]
    assert "capacityProviderArn" in provider
    assert provider["name"] == "my_provider"
    assert provider["tags"] == [{"key": "k1", "value": "v1"}]

    client.tag_resource(
        resourceArn=provider["capacityProviderArn"], tags=[{"key": "k2", "value": "v2"}]
    )

    resp = client.list_tags_for_resource(resourceArn=provider["capacityProviderArn"])
    assert len(resp["tags"]) == 2
    assert {"key": "k1", "value": "v1"} in resp["tags"]
    assert {"key": "k2", "value": "v2"} in resp["tags"]

    client.untag_resource(resourceArn=provider["capacityProviderArn"], tagKeys=["k1"])

    resp = client.list_tags_for_resource(resourceArn=provider["capacityProviderArn"])
    assert resp["tags"] == [{"key": "k2", "value": "v2"}]


@mock_ecs
def test_describe_capacity_provider__using_name():
    client = boto3.client("ecs", region_name="us-west-1")
    client.create_capacity_provider(
        name="my_provider",
        autoScalingGroupProvider={
            "autoScalingGroupArn": "asg:arn",
            "managedScaling": {
                "status": "ENABLED",
                "targetCapacity": 5,
                "maximumScalingStepSize": 2,
            },
            "managedTerminationProtection": "DISABLED",
        },
    )

    resp = client.describe_capacity_providers(capacityProviders=["my_provider"])
    assert len(resp["capacityProviders"]) == 1

    provider = resp["capacityProviders"][0]
    assert "capacityProviderArn" in provider
    assert provider["name"] == "my_provider"
    assert provider["status"] == "ACTIVE"
    assert provider["autoScalingGroupProvider"] == {
        "autoScalingGroupArn": "asg:arn",
        "managedScaling": {
            "instanceWarmupPeriod": 300,
            "status": "ENABLED",
            "targetCapacity": 5,
            "minimumScalingStepSize": 1,
            "maximumScalingStepSize": 2,
        },
        "managedTerminationProtection": "DISABLED",
    }


@mock_ecs
def test_describe_capacity_provider__using_arn():
    client = boto3.client("ecs", region_name="us-west-1")
    provider_arn = client.create_capacity_provider(
        name="my_provider",
        autoScalingGroupProvider={
            "autoScalingGroupArn": "asg:arn",
            "managedScaling": {
                "status": "ENABLED",
                "targetCapacity": 5,
                "maximumScalingStepSize": 2,
            },
            "managedTerminationProtection": "DISABLED",
        },
    )["capacityProvider"]["capacityProviderArn"]

    resp = client.describe_capacity_providers(capacityProviders=[provider_arn])
    assert len(resp["capacityProviders"]) == 1

    provider = resp["capacityProviders"][0]
    assert provider["name"] == "my_provider"


@mock_ecs
def test_describe_capacity_provider__missing():
    client = boto3.client("ecs", region_name="us-west-1")
    client.create_capacity_provider(
        name="my_provider",
        autoScalingGroupProvider={
            "autoScalingGroupArn": "asg:arn",
            "managedScaling": {
                "status": "ENABLED",
                "targetCapacity": 5,
                "maximumScalingStepSize": 2,
            },
            "managedTerminationProtection": "DISABLED",
        },
    )

    resp = client.describe_capacity_providers(
        capacityProviders=["my_provider", "another_provider"]
    )
    assert len(resp["capacityProviders"]) == 1
    assert resp["failures"] == [
        {
            "arn": f"arn:aws:ecs:us-west-1:{ACCOUNT_ID}:capacity_provider/another_provider",
            "reason": "MISSING",
        }
    ]


@mock_ecs
def test_delete_capacity_provider():
    client = boto3.client("ecs", region_name="us-west-1")
    client.create_capacity_provider(
        name="my_provider", autoScalingGroupProvider={"autoScalingGroupArn": "asg:arn"}
    )

    resp = client.delete_capacity_provider(capacityProvider="my_provider")
    assert resp["capacityProvider"]["name"] == "my_provider"

    # We can't find either provider
    resp = client.describe_capacity_providers(
        capacityProviders=["my_provider", "another_provider"]
    )
    assert resp["capacityProviders"] == []
    assert len(resp["failures"]) == 2
    assert {
        "arn": f"arn:aws:ecs:us-west-1:{ACCOUNT_ID}:capacity_provider/another_provider",
        "reason": "MISSING",
    } in resp["failures"]
    assert {
        "arn": f"arn:aws:ecs:us-west-1:{ACCOUNT_ID}:capacity_provider/my_provider",
        "reason": "MISSING",
    } in resp["failures"]


@mock_ecs
def test_update_capacity_provider():
    client = boto3.client("ecs", region_name="us-west-1")
    client.create_capacity_provider(
        name="my_provider", autoScalingGroupProvider={"autoScalingGroupArn": "asg:arn"}
    )

    resp = client.update_capacity_provider(
        name="my_provider",
        autoScalingGroupProvider={
            "managedScaling": {"status": "ENABLED", "instanceWarmupPeriod": 0}
        },
    )
    assert resp["capacityProvider"]["name"] == "my_provider"

    # We can't find either provider
    provider = client.describe_capacity_providers(capacityProviders=["my_provider"])[
        "capacityProviders"
    ][0]
    assert provider["autoScalingGroupProvider"] == {
        "autoScalingGroupArn": "asg:arn",
        "managedScaling": {
            "instanceWarmupPeriod": 0,
            "maximumScalingStepSize": 10000,
            "minimumScalingStepSize": 1,
            "status": "ENABLED",
            "targetCapacity": 100,
        },
        "managedTerminationProtection": "DISABLED",
    }
