import boto3

from moto import mock_ecs
from moto.core import ACCOUNT_ID


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
    resp.should.have.key("capacityProvider")

    provider = resp["capacityProvider"]
    provider.should.have.key("capacityProviderArn")
    provider.should.have.key("name").equals("my_provider")
    provider.should.have.key("status").equals("ACTIVE")
    provider.should.have.key("autoScalingGroupProvider").equals(
        {
            "autoScalingGroupArn": "asg:arn",
            "managedScaling": {
                "status": "ENABLED",
                "targetCapacity": 5,
                "maximumScalingStepSize": 2,
            },
            "managedTerminationProtection": "DISABLED",
        }
    )


@mock_ecs
def test_create_capacity_provider_with_tags():
    client = boto3.client("ecs", region_name="us-west-1")
    resp = client.create_capacity_provider(
        name="my_provider",
        autoScalingGroupProvider={"autoScalingGroupArn": "asg:arn"},
        tags=[{"key": "k1", "value": "v1"}],
    )
    resp.should.have.key("capacityProvider")

    provider = resp["capacityProvider"]
    provider.should.have.key("capacityProviderArn")
    provider.should.have.key("name").equals("my_provider")
    provider.should.have.key("tags").equals([{"key": "k1", "value": "v1"}])


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
    resp.should.have.key("capacityProviders").length_of(1)

    provider = resp["capacityProviders"][0]
    provider.should.have.key("capacityProviderArn")
    provider.should.have.key("name").equals("my_provider")
    provider.should.have.key("status").equals("ACTIVE")
    provider.should.have.key("autoScalingGroupProvider").equals(
        {
            "autoScalingGroupArn": "asg:arn",
            "managedScaling": {
                "status": "ENABLED",
                "targetCapacity": 5,
                "maximumScalingStepSize": 2,
            },
            "managedTerminationProtection": "DISABLED",
        }
    )


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
    resp.should.have.key("capacityProviders").length_of(1)

    provider = resp["capacityProviders"][0]
    provider.should.have.key("name").equals("my_provider")


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
    resp.should.have.key("capacityProviders").length_of(1)
    resp.should.have.key("failures").length_of(1)
    resp["failures"].should.contain(
        {
            "arn": f"arn:aws:ecs:us-west-1:{ACCOUNT_ID}:capacity_provider/another_provider",
            "reason": "MISSING",
        }
    )


@mock_ecs
def test_delete_capacity_provider():
    client = boto3.client("ecs", region_name="us-west-1")
    client.create_capacity_provider(
        name="my_provider", autoScalingGroupProvider={"autoScalingGroupArn": "asg:arn"}
    )

    resp = client.delete_capacity_provider(capacityProvider="my_provider")
    resp.should.have.key("capacityProvider")
    resp["capacityProvider"].should.have.key("name").equals("my_provider")

    # We can't find either provider
    resp = client.describe_capacity_providers(
        capacityProviders=["my_provider", "another_provider"]
    )
    resp.should.have.key("capacityProviders").length_of(0)
    resp.should.have.key("failures").length_of(2)
    resp["failures"].should.contain(
        {
            "arn": f"arn:aws:ecs:us-west-1:{ACCOUNT_ID}:capacity_provider/another_provider",
            "reason": "MISSING",
        }
    )
    resp["failures"].should.contain(
        {
            "arn": f"arn:aws:ecs:us-west-1:{ACCOUNT_ID}:capacity_provider/my_provider",
            "reason": "MISSING",
        }
    )
