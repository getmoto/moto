import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@pytest.fixture(name="region_name")
def fixture_region_name():
    return "ap-northeast-1"


@pytest.fixture(name="iot_client")
def fixture_iot_client(region_name):
    with mock_aws():
        yield boto3.client("iot", region_name=region_name)


@pytest.fixture(name="policy")
def fixture_policy(iot_client):
    return iot_client.create_policy(policyName="my-policy", policyDocument="{}")


def test_attach_policy(iot_client, policy):
    policy_name = policy["policyName"]

    cert = iot_client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]
    iot_client.attach_policy(policyName=policy_name, target=cert_arn)

    res = iot_client.list_attached_policies(target=cert_arn)
    assert len(res["policies"]) == 1
    assert res["policies"][0]["policyName"] == "my-policy"

    res = iot_client.list_attached_policies(target=cert_arn)
    assert len(res["policies"]) == 1
    assert res["policies"][0]["policyName"] == "my-policy"


@mock_aws
def test_attach_policy_to_identity(region_name, iot_client, policy):
    cognito_identity_client = boto3.client("cognito-identity", region_name=region_name)
    identity_pool_name = "test_identity_pool"
    identity_pool = cognito_identity_client.create_identity_pool(
        IdentityPoolName=identity_pool_name, AllowUnauthenticatedIdentities=True
    )
    identity = cognito_identity_client.get_id(
        AccountId="test", IdentityPoolId=identity_pool["IdentityPoolId"]
    )

    client = iot_client
    policy_name = policy["policyName"]
    client.attach_policy(policyName=policy_name, target=identity["IdentityId"])

    res = client.list_attached_policies(target=identity["IdentityId"])
    assert len(res["policies"]) == 1
    assert res["policies"][0]["policyName"] == policy_name


def test_detach_policy(iot_client, policy):
    cert = iot_client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    policy_name = policy["policyName"]
    iot_client.attach_policy(policyName=policy_name, target=cert_arn)

    res = iot_client.list_attached_policies(target=cert_arn)
    assert len(res["policies"]) == 1
    assert res["policies"][0]["policyName"] == policy_name

    iot_client.detach_policy(policyName=policy_name, target=cert_arn)
    res = iot_client.list_attached_policies(target=cert_arn)
    assert res["policies"] == []


def test_list_attached_policies(iot_client):
    cert = iot_client.create_keys_and_certificate(setAsActive=True)
    policies = iot_client.list_attached_policies(target=cert["certificateArn"])
    assert policies["policies"] == []


def test_policy_versions(iot_client):
    policy_name = "my-policy"
    doc = "{}"

    policy = iot_client.create_policy(policyName=policy_name, policyDocument=doc)
    assert policy["policyName"] == policy_name
    assert policy["policyArn"] is not None
    assert policy["policyDocument"] == json.dumps({})
    assert policy["policyVersionId"] == "1"

    policy = iot_client.get_policy(policyName=policy_name)
    assert policy["policyName"] == policy_name
    assert policy["policyArn"] is not None
    assert policy["policyDocument"] == json.dumps({})
    assert policy["defaultVersionId"] == policy["defaultVersionId"]

    policy1 = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_1"}),
        setAsDefault=True,
    )
    assert policy1["policyArn"] is not None
    assert policy1["policyDocument"] == json.dumps({"version": "version_1"})
    assert policy1["policyVersionId"] == "2"
    assert policy1["isDefaultVersion"] is True

    policy2 = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_2"}),
        setAsDefault=False,
    )
    assert policy2["policyArn"] is not None
    assert policy2["policyDocument"] == json.dumps({"version": "version_2"})
    assert policy2["policyVersionId"] == "3"
    assert policy2["isDefaultVersion"] is False

    policy = iot_client.get_policy(policyName=policy_name)
    assert policy["policyName"] == policy_name
    assert policy["policyArn"] is not None
    assert policy["policyDocument"] == json.dumps({"version": "version_1"})
    assert policy["defaultVersionId"] == policy1["policyVersionId"]

    policy3 = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_3"}),
        setAsDefault=False,
    )
    assert policy3["policyArn"] is not None
    assert policy3["policyDocument"] == json.dumps({"version": "version_3"})
    assert policy3["policyVersionId"] == "4"
    assert policy3["isDefaultVersion"] is False

    policy4 = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_4"}),
        setAsDefault=False,
    )
    assert policy4["policyArn"] is not None
    assert policy4["policyDocument"] == json.dumps({"version": "version_4"})
    assert policy4["policyVersionId"] == "5"
    assert policy4["isDefaultVersion"] is False

    policy_versions = iot_client.list_policy_versions(policyName=policy_name)[
        "policyVersions"
    ]
    assert len(policy_versions) == 5
    assert (
        list(map(lambda item: item["isDefaultVersion"], policy_versions)).count(True)
        == 1
    )
    default_policy = list(
        filter(lambda item: item["isDefaultVersion"], policy_versions)
    )
    assert default_policy[0]["versionId"] == policy1["policyVersionId"]

    policy = iot_client.get_policy(policyName=policy_name)
    assert policy["policyName"] == policy_name
    assert policy["policyArn"] is not None
    assert policy["policyDocument"] == json.dumps({"version": "version_1"})
    assert policy["defaultVersionId"] == policy1["policyVersionId"]

    iot_client.set_default_policy_version(
        policyName=policy_name, policyVersionId=policy4["policyVersionId"]
    )
    policy_versions = iot_client.list_policy_versions(policyName=policy_name)[
        "policyVersions"
    ]
    assert len(policy_versions) == 5
    assert (
        list(map(lambda item: item["isDefaultVersion"], policy_versions)).count(True)
        == 1
    )
    default_policy = list(
        filter(lambda item: item["isDefaultVersion"], policy_versions)
    )
    assert default_policy[0]["versionId"] == policy4["policyVersionId"]

    policy = iot_client.get_policy(policyName=policy_name)
    assert policy["policyName"] == policy_name
    assert policy["policyArn"] is not None
    assert policy["policyDocument"] == json.dumps({"version": "version_4"})
    assert policy["defaultVersionId"] == policy4["policyVersionId"]

    with pytest.raises(ClientError) as exc:
        iot_client.create_policy_version(
            policyName=policy_name,
            policyDocument=json.dumps({"version": "version_5"}),
            setAsDefault=False,
        )
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == f"The policy {policy_name} already has the maximum number of versions (5)"
    )

    iot_client.delete_policy_version(policyName=policy_name, policyVersionId="1")
    policy_versions = iot_client.list_policy_versions(policyName=policy_name)
    assert len(policy_versions["policyVersions"]) == 4

    iot_client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy1["policyVersionId"]
    )
    policy_versions = iot_client.list_policy_versions(policyName=policy_name)
    assert len(policy_versions["policyVersions"]) == 3
    iot_client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy2["policyVersionId"]
    )
    policy_versions = iot_client.list_policy_versions(policyName=policy_name)
    assert len(policy_versions["policyVersions"]) == 2

    iot_client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy3["policyVersionId"]
    )
    policy_versions = iot_client.list_policy_versions(policyName=policy_name)
    assert len(policy_versions["policyVersions"]) == 1

    # should fail as it"s the default policy. Should use delete_policy instead
    with pytest.raises(ClientError) as exc:
        iot_client.delete_policy_version(
            policyName=policy_name, policyVersionId=policy4["policyVersionId"]
        )
    err = exc.value.response["Error"]
    assert err["Message"] == "Cannot delete the default version of a policy"


def test_policy_versions_increment_beyond_5(iot_client, policy):
    """
    Version ids increment by one each time.

    Previously there was a bug where the version id was not incremented beyond 5.
    This prevents a regression.
    """
    policy_name = policy["policyName"]

    for v in range(2, 11):
        new_version = iot_client.create_policy_version(
            policyName=policy_name,
            policyDocument=json.dumps({"version": f"version_{v}"}),
            setAsDefault=True,
        )
        assert new_version["policyVersionId"] == str(v)
        iot_client.delete_policy_version(
            policyName=policy_name, policyVersionId=str(v - 1)
        )


def test_policy_versions_increment_even_after_version_delete(iot_client, policy):
    """Version ids increment even if the max version was deleted."""

    policy_name = policy["policyName"]

    new_version = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_2"}),
    )
    assert new_version["policyVersionId"] == "2"
    iot_client.delete_policy_version(policyName=policy_name, policyVersionId="2")
    third_version = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_3"}),
    )
    assert third_version["policyVersionId"] == "3"


def test_delete_policy_validation(iot_client):
    doc = """{
    "Version": "2012-10-17",
    "Statement":[
        {
            "Effect":"Allow",
            "Action":[
                "iot: *"
            ],
            "Resource":"*"
        }
      ]
    }
    """
    cert = iot_client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]
    policy_name = "my-policy"
    iot_client.create_policy(policyName=policy_name, policyDocument=doc)
    iot_client.attach_principal_policy(policyName=policy_name, principal=cert_arn)

    with pytest.raises(ClientError) as e:
        iot_client.delete_policy(policyName=policy_name)
    assert (
        f"The policy cannot be deleted as the policy is attached to one or more principals (name={policy_name})"
        in e.value.response["Error"]["Message"]
    )
    res = iot_client.list_policies()
    assert len(res["policies"]) == 1

    iot_client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    iot_client.delete_policy(policyName=policy_name)
    res = iot_client.list_policies()
    assert len(res["policies"]) == 0


def test_policy(iot_client):
    name = "my-policy"
    doc = "{}"
    policy = iot_client.create_policy(policyName=name, policyDocument=doc)
    assert policy["policyName"] == name
    assert policy["policyArn"] is not None
    assert policy["policyDocument"] == doc
    assert policy["policyVersionId"] == "1"

    policy = iot_client.get_policy(policyName=name)
    assert policy["policyName"] == name
    assert policy["policyArn"] is not None
    assert policy["policyDocument"] == doc
    assert policy["defaultVersionId"] == "1"

    res = iot_client.list_policies()
    assert len(res["policies"]) == 1
    for policy in res["policies"]:
        assert policy["policyName"] is not None
        assert policy["policyArn"] is not None

    iot_client.delete_policy(policyName=name)
    res = iot_client.list_policies()
    assert len(res["policies"]) == 0


def test_attach_policy_to_thing_group(iot_client, policy):
    thing_group = iot_client.create_thing_group(thingGroupName="my-thing-group")
    thing_group_arn = thing_group["thingGroupArn"]

    policy_name = policy["policyName"]
    iot_client.attach_policy(policyName=policy_name, target=thing_group_arn)

    res = iot_client.list_attached_policies(target=thing_group_arn)
    assert len(res["policies"]) == 1
    assert res["policies"][0]["policyName"] == policy_name


def test_attach_policy_to_non_existant_thing_group_raises_ResourceNotFoundException(
    iot_client, policy
):
    thing_group_arn = (
        "arn:aws:iot:ap-northeast-1:123456789012:thinggroup/my-thing-group"
    )
    policy_name = policy["policyName"]

    with pytest.raises(ClientError, match=thing_group_arn):
        iot_client.attach_policy(policyName=policy_name, target=thing_group_arn)


def test_policy_delete_fails_when_versions_exist(iot_client, policy):
    policy_name = policy["policyName"]
    iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=policy["policyDocument"],
        setAsDefault=True,
    )
    with pytest.raises(ClientError) as e:
        iot_client.delete_policy(policyName=policy_name)
    assert (
        "Cannot delete the policy because it has one or more policy versions attached to it"
        in e.value.response["Error"]["Message"]
    )


def test_list_targets_for_policy_empty(iot_client, policy):
    res = iot_client.list_targets_for_policy(policyName=policy["policyName"])
    assert len(res["targets"]) == 0


def test_list_targets_for_policy_one_attached_thing_group(iot_client, policy):
    thing_group = iot_client.create_thing_group(thingGroupName="my-thing-group")
    thing_group_arn = thing_group["thingGroupArn"]

    policy_name = policy["policyName"]
    iot_client.attach_policy(policyName=policy_name, target=thing_group_arn)

    res = iot_client.list_targets_for_policy(policyName=policy["policyName"])
    assert len(res["targets"]) == 1
    assert res["targets"][0] == thing_group_arn


def test_list_targets_for_policy_one_attached_certificate(iot_client, policy):
    cert = iot_client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    policy_name = policy["policyName"]
    iot_client.attach_policy(policyName=policy_name, target=cert_arn)

    res = iot_client.list_targets_for_policy(policyName=policy["policyName"])
    assert len(res["targets"]) == 1
    assert res["targets"][0] == cert_arn


def test_list_targets_for_policy_resource_not_found(iot_client):
    with pytest.raises(ClientError) as e:
        iot_client.list_targets_for_policy(policyName="NON_EXISTENT_POLICY_NAME")

    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert "Policy not found" in e.value.response["Error"]["Message"]


def test_create_policy_fails_when_name_taken(iot_client, policy):
    policy_name = policy["policyName"]

    with pytest.raises(ClientError) as e:
        iot_client.create_policy(
            policyName=policy_name,
            policyDocument='{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}',
        )

    current_policy = iot_client.get_policy(policyName=policy_name)
    assert e.value.response["Error"]["Code"] == "ResourceAlreadyExistsException"
    assert (
        e.value.response["Error"]["Message"]
        == f"Policy cannot be created - name already exists (name={policy_name})"
    )

    # the policy should not have been overwritten
    assert current_policy["policyDocument"] == policy["policyDocument"]
