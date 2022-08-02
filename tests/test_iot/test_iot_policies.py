import boto3
import json
import pytest

from botocore.exceptions import ClientError
from moto import mock_iot, mock_cognitoidentity


@pytest.fixture
def region_name():
    return "ap-northeast-1"


@pytest.fixture
def iot_client(region_name):
    with mock_iot():
        yield boto3.client("iot", region_name=region_name)


@pytest.fixture
def policy(iot_client):
    return iot_client.create_policy(policyName="my-policy", policyDocument="{}")


def test_attach_policy(iot_client, policy):
    policy_name = policy["policyName"]

    cert = iot_client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]
    iot_client.attach_policy(policyName=policy_name, target=cert_arn)

    res = iot_client.list_attached_policies(target=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    res["policies"][0]["policyName"].should.equal("my-policy")


@mock_cognitoidentity
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
    res.should.have.key("policies").which.should.have.length_of(1)
    res["policies"][0]["policyName"].should.equal(policy_name)


def test_detach_policy(iot_client, policy):

    cert = iot_client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    policy_name = policy["policyName"]
    iot_client.attach_policy(policyName=policy_name, target=cert_arn)

    res = iot_client.list_attached_policies(target=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    res["policies"][0]["policyName"].should.equal(policy_name)

    iot_client.detach_policy(policyName=policy_name, target=cert_arn)
    res = iot_client.list_attached_policies(target=cert_arn)
    res.should.have.key("policies").which.should.be.empty


def test_list_attached_policies(iot_client):
    cert = iot_client.create_keys_and_certificate(setAsActive=True)
    policies = iot_client.list_attached_policies(target=cert["certificateArn"])
    policies["policies"].should.equal([])


def test_policy_versions(iot_client):
    policy_name = "my-policy"
    doc = "{}"

    policy = iot_client.create_policy(policyName=policy_name, policyDocument=doc)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(json.dumps({}))
    policy.should.have.key("policyVersionId").which.should.equal("1")

    policy = iot_client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(json.dumps({}))
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy["defaultVersionId"]
    )

    policy1 = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_1"}),
        setAsDefault=True,
    )
    policy1.should.have.key("policyArn").which.should_not.be.none
    policy1.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_1"})
    )
    policy1.should.have.key("policyVersionId").which.should.equal("2")
    policy1.should.have.key("isDefaultVersion").which.should.equal(True)

    policy2 = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_2"}),
        setAsDefault=False,
    )
    policy2.should.have.key("policyArn").which.should_not.be.none
    policy2.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_2"})
    )
    policy2.should.have.key("policyVersionId").which.should.equal("3")
    policy2.should.have.key("isDefaultVersion").which.should.equal(False)

    policy = iot_client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_1"})
    )
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy1["policyVersionId"]
    )

    policy3 = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_3"}),
        setAsDefault=False,
    )
    policy3.should.have.key("policyArn").which.should_not.be.none
    policy3.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_3"})
    )
    policy3.should.have.key("policyVersionId").which.should.equal("4")
    policy3.should.have.key("isDefaultVersion").which.should.equal(False)

    policy4 = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_4"}),
        setAsDefault=False,
    )
    policy4.should.have.key("policyArn").which.should_not.be.none
    policy4.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_4"})
    )
    policy4.should.have.key("policyVersionId").which.should.equal("5")
    policy4.should.have.key("isDefaultVersion").which.should.equal(False)

    policy_versions = iot_client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(5)
    list(
        map(lambda item: item["isDefaultVersion"], policy_versions["policyVersions"])
    ).count(True).should.equal(1)
    default_policy = list(
        filter(lambda item: item["isDefaultVersion"], policy_versions["policyVersions"])
    )
    default_policy[0].should.have.key("versionId").should.equal(
        policy1["policyVersionId"]
    )

    policy = iot_client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_1"})
    )
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy1["policyVersionId"]
    )

    iot_client.set_default_policy_version(
        policyName=policy_name, policyVersionId=policy4["policyVersionId"]
    )
    policy_versions = iot_client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(5)
    list(
        map(lambda item: item["isDefaultVersion"], policy_versions["policyVersions"])
    ).count(True).should.equal(1)
    default_policy = list(
        filter(lambda item: item["isDefaultVersion"], policy_versions["policyVersions"])
    )
    default_policy[0].should.have.key("versionId").should.equal(
        policy4["policyVersionId"]
    )

    policy = iot_client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_4"})
    )
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy4["policyVersionId"]
    )

    with pytest.raises(ClientError) as exc:
        iot_client.create_policy_version(
            policyName=policy_name,
            policyDocument=json.dumps({"version": "version_5"}),
            setAsDefault=False,
        )
    err = exc.value.response["Error"]
    err["Message"].should.equal(
        "The policy %s already has the maximum number of versions (5)" % policy_name
    )

    iot_client.delete_policy_version(policyName=policy_name, policyVersionId="1")
    policy_versions = iot_client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(4)

    iot_client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy1["policyVersionId"]
    )
    policy_versions = iot_client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(3)
    iot_client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy2["policyVersionId"]
    )
    policy_versions = iot_client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(2)

    iot_client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy3["policyVersionId"]
    )
    policy_versions = iot_client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(1)

    # should fail as it"s the default policy. Should use delete_policy instead
    with pytest.raises(ClientError) as exc:
        iot_client.delete_policy_version(
            policyName=policy_name, policyVersionId=policy4["policyVersionId"]
        )
    err = exc.value.response["Error"]
    err["Message"].should.equal("Cannot delete the default version of a policy")


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
        new_version.should.have.key("policyVersionId").which.should.equal(str(v))
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
    new_version.should.have.key("policyVersionId").which.should.equal("2")
    iot_client.delete_policy_version(policyName=policy_name, policyVersionId="2")
    third_version = iot_client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_3"}),
    )
    third_version.should.have.key("policyVersionId").which.should.equal("3")


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
    e.value.response["Error"]["Message"].should.contain(
        "The policy cannot be deleted as the policy is attached to one or more principals (name=%s)"
        % policy_name
    )
    res = iot_client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(1)

    iot_client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    iot_client.delete_policy(policyName=policy_name)
    res = iot_client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(0)


def test_policy(iot_client):
    name = "my-policy"
    doc = "{}"
    policy = iot_client.create_policy(policyName=name, policyDocument=doc)
    policy.should.have.key("policyName").which.should.equal(name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(doc)
    policy.should.have.key("policyVersionId").which.should.equal("1")

    policy = iot_client.get_policy(policyName=name)
    policy.should.have.key("policyName").which.should.equal(name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(doc)
    policy.should.have.key("defaultVersionId").which.should.equal("1")

    res = iot_client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(1)
    for policy in res["policies"]:
        policy.should.have.key("policyName").which.should_not.be.none
        policy.should.have.key("policyArn").which.should_not.be.none

    iot_client.delete_policy(policyName=name)
    res = iot_client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(0)


def test_attach_policy_to_thing_group(iot_client, policy):
    thing_group = iot_client.create_thing_group(thingGroupName="my-thing-group")
    thing_group_arn = thing_group["thingGroupArn"]

    policy_name = policy["policyName"]
    iot_client.attach_policy(policyName=policy_name, target=thing_group_arn)

    res = iot_client.list_attached_policies(target=thing_group_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    res["policies"][0]["policyName"].should.equal(policy_name)


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
    e.value.response["Error"]["Message"].should.contain(
        "Cannot delete the policy because it has one or more policy versions attached to it"
    )


def test_list_targets_for_policy_empty(iot_client, policy):
    res = iot_client.list_targets_for_policy(policyName=policy["policyName"])
    res.should.have.key("targets").which.should.have.length_of(0)


def test_list_targets_for_policy_one_attached_thing_group(iot_client, policy):
    thing_group = iot_client.create_thing_group(thingGroupName="my-thing-group")
    thing_group_arn = thing_group["thingGroupArn"]

    policy_name = policy["policyName"]
    iot_client.attach_policy(policyName=policy_name, target=thing_group_arn)

    res = iot_client.list_targets_for_policy(policyName=policy["policyName"])
    res.should.have.key("targets").which.should.have.length_of(1)
    res["targets"][0].should.equal(thing_group_arn)


def test_list_targets_for_policy_one_attached_certificate(iot_client, policy):
    cert = iot_client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    policy_name = policy["policyName"]
    iot_client.attach_policy(policyName=policy_name, target=cert_arn)

    res = iot_client.list_targets_for_policy(policyName=policy["policyName"])
    res.should.have.key("targets").which.should.have.length_of(1)
    res["targets"][0].should.equal(cert_arn)


def test_list_targets_for_policy_resource_not_found(iot_client):
    with pytest.raises(ClientError) as e:
        iot_client.list_targets_for_policy(policyName="NON_EXISTENT_POLICY_NAME")

    e.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    e.value.response["Error"]["Message"].should.contain("Policy not found")


def test_create_policy_fails_when_name_taken(iot_client, policy):
    policy_name = policy["policyName"]

    with pytest.raises(ClientError) as e:
        iot_client.create_policy(
            policyName=policy_name,
            policyDocument='{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}',
        )

    current_policy = iot_client.get_policy(policyName=policy_name)
    e.value.response["Error"]["Code"].should.equal("ResourceAlreadyExistsException")
    e.value.response["Error"]["Message"].should.equal(
        f"Policy cannot be created - name already exists (name={policy_name})"
    )

    # the policy should not have been overwritten
    current_policy.should.have.key("policyDocument").which.should.equal(
        policy["policyDocument"]
    )
