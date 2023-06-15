import boto3

from moto import mock_batch
from tests import DEFAULT_ACCOUNT_ID


@mock_batch
def test_create_scheduling_policy():
    client = boto3.client("batch", "us-east-2")
    resp = client.create_scheduling_policy(name="test")
    assert resp["name"] == "test"
    assert (
        resp["arn"]
        == f"arn:aws:batch:us-east-2:{DEFAULT_ACCOUNT_ID}:scheduling-policy/test"
    )


@mock_batch
def test_describe_default_scheduling_policy():
    client = boto3.client("batch", "us-east-2")
    arn = client.create_scheduling_policy(name="test")["arn"]

    resp = client.describe_scheduling_policies(arns=[arn])
    assert len(resp["schedulingPolicies"]) == 1

    policy = resp["schedulingPolicies"][0]
    assert policy["arn"] == arn
    assert policy["fairsharePolicy"] == {
        "computeReservation": 0,
        "shareDecaySeconds": 0,
        "shareDistribution": [],
    }
    assert policy["tags"] == {}


@mock_batch
def test_describe_scheduling_policy():
    client = boto3.client("batch", "us-east-2")
    arn = client.create_scheduling_policy(
        name="test",
        fairsharePolicy={
            "shareDecaySeconds": 1,
            "computeReservation": 2,
            "shareDistribution": [{"shareIdentifier": "A", "weightFactor": 0.1}],
        },
    )["arn"]

    resp = client.list_scheduling_policies()
    assert "schedulingPolicies" in resp
    arns = [a["arn"] for a in resp["schedulingPolicies"]]
    assert arn in arns

    resp = client.describe_scheduling_policies(arns=[arn])
    assert len(resp["schedulingPolicies"]) == 1

    policy = resp["schedulingPolicies"][0]
    assert policy["arn"] == arn
    assert policy["fairsharePolicy"] == {
        "computeReservation": 2,
        "shareDecaySeconds": 1,
        "shareDistribution": [{"shareIdentifier": "A", "weightFactor": 0.1}],
    }
    assert policy["tags"] == {}


@mock_batch
def test_delete_scheduling_policy():
    client = boto3.client("batch", "us-east-2")
    arn = client.create_scheduling_policy(name="test")["arn"]

    client.delete_scheduling_policy(arn=arn)

    resp = client.describe_scheduling_policies(arns=[arn])
    assert len(resp["schedulingPolicies"]) == 0


@mock_batch
def test_update_scheduling_policy():
    client = boto3.client("batch", "us-east-2")
    arn = client.create_scheduling_policy(name="test")["arn"]

    client.update_scheduling_policy(
        arn=arn,
        fairsharePolicy={
            "computeReservation": 5,
            "shareDecaySeconds": 10,
            "shareDistribution": [],
        },
    )

    resp = client.describe_scheduling_policies(arns=[arn])
    assert len(resp["schedulingPolicies"]) == 1

    policy = resp["schedulingPolicies"][0]
    assert policy["arn"] == arn
    assert policy["fairsharePolicy"] == {
        "computeReservation": 5,
        "shareDecaySeconds": 10,
        "shareDistribution": [],
    }
