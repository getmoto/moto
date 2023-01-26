import boto3

from moto import mock_batch
from tests import DEFAULT_ACCOUNT_ID


@mock_batch
def test_create_scheduling_policy():
    client = boto3.client("batch", "us-east-2")
    resp = client.create_scheduling_policy(name="test")
    resp.should.have.key("name").equals("test")
    resp.should.have.key("arn").equals(
        f"arn:aws:batch:us-east-2:{DEFAULT_ACCOUNT_ID}:scheduling-policy/test"
    )


@mock_batch
def test_describe_default_scheduling_policy():
    client = boto3.client("batch", "us-east-2")
    arn = client.create_scheduling_policy(name="test")["arn"]

    resp = client.describe_scheduling_policies(arns=[arn])
    resp.should.have.key("schedulingPolicies").length_of(1)

    policy = resp["schedulingPolicies"][0]
    policy["arn"].should.equal(arn)
    policy["fairsharePolicy"].should.equal(
        {"computeReservation": 0, "shareDecaySeconds": 0, "shareDistribution": []}
    )
    policy["tags"].should.equal({})


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
    resp.should.have.key("schedulingPolicies")
    arns = [a["arn"] for a in resp["schedulingPolicies"]]
    arns.should.contain(arn)

    resp = client.describe_scheduling_policies(arns=[arn])
    resp.should.have.key("schedulingPolicies").length_of(1)

    policy = resp["schedulingPolicies"][0]
    policy["arn"].should.equal(arn)
    policy["fairsharePolicy"].should.equal(
        {
            "computeReservation": 2,
            "shareDecaySeconds": 1,
            "shareDistribution": [{"shareIdentifier": "A", "weightFactor": 0.1}],
        }
    )
    policy["tags"].should.equal({})


@mock_batch
def test_delete_scheduling_policy():
    client = boto3.client("batch", "us-east-2")
    arn = client.create_scheduling_policy(name="test")["arn"]

    client.delete_scheduling_policy(arn=arn)

    resp = client.describe_scheduling_policies(arns=[arn])
    resp.should.have.key("schedulingPolicies").length_of(0)


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
    resp.should.have.key("schedulingPolicies").length_of(1)

    policy = resp["schedulingPolicies"][0]
    policy["arn"].should.equal(arn)
    policy["fairsharePolicy"].should.equal(
        {"computeReservation": 5, "shareDecaySeconds": 10, "shareDistribution": []}
    )
