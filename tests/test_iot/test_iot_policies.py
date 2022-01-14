import boto3
import json
import pytest

from botocore.exceptions import ClientError
from moto import mock_iot, mock_cognitoidentity


@mock_iot
def test_attach_policy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    policy_name = "my-policy"
    doc = "{}"

    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_attached_policies(target=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    res["policies"][0]["policyName"].should.equal("my-policy")


@mock_iot
@mock_cognitoidentity
def test_attach_policy_to_identity():
    region = "ap-northeast-1"

    cognito_identity_client = boto3.client("cognito-identity", region_name=region)
    identity_pool_name = "test_identity_pool"
    identity_pool = cognito_identity_client.create_identity_pool(
        IdentityPoolName=identity_pool_name, AllowUnauthenticatedIdentities=True
    )
    identity = cognito_identity_client.get_id(
        AccountId="test", IdentityPoolId=identity_pool["IdentityPoolId"]
    )

    client = boto3.client("iot", region_name=region)
    policy_name = "my-policy"
    doc = "{}"
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_policy(policyName=policy_name, target=identity["IdentityId"])

    res = client.list_attached_policies(target=identity["IdentityId"])
    res.should.have.key("policies").which.should.have.length_of(1)
    res["policies"][0]["policyName"].should.equal(policy_name)


@mock_iot
def test_detach_policy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    policy_name = "my-policy"
    doc = "{}"

    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_attached_policies(target=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    res["policies"][0]["policyName"].should.equal("my-policy")

    client.detach_policy(policyName=policy_name, target=cert_arn)
    res = client.list_attached_policies(target=cert_arn)
    res.should.have.key("policies").which.should.be.empty


@mock_iot
def test_list_attached_policies():
    client = boto3.client("iot", region_name="ap-northeast-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    policies = client.list_attached_policies(target=cert["certificateArn"])
    policies["policies"].should.be.empty


@mock_iot
def test_policy_versions():
    client = boto3.client("iot", region_name="ap-northeast-1")
    policy_name = "my-policy"
    doc = "{}"

    policy = client.create_policy(policyName=policy_name, policyDocument=doc)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(json.dumps({}))
    policy.should.have.key("policyVersionId").which.should.equal("1")

    policy = client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(json.dumps({}))
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy["defaultVersionId"]
    )

    policy1 = client.create_policy_version(
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

    policy2 = client.create_policy_version(
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

    policy = client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_1"})
    )
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy1["policyVersionId"]
    )

    policy3 = client.create_policy_version(
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

    policy4 = client.create_policy_version(
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

    policy_versions = client.list_policy_versions(policyName=policy_name)
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

    policy = client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_1"})
    )
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy1["policyVersionId"]
    )

    client.set_default_policy_version(
        policyName=policy_name, policyVersionId=policy4["policyVersionId"]
    )
    policy_versions = client.list_policy_versions(policyName=policy_name)
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

    policy = client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_4"})
    )
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy4["policyVersionId"]
    )

    with pytest.raises(ClientError) as exc:
        client.create_policy_version(
            policyName=policy_name,
            policyDocument=json.dumps({"version": "version_5"}),
            setAsDefault=False,
        )
    err = exc.value.response["Error"]
    err["Message"].should.equal(
        "The policy %s already has the maximum number of versions (5)" % policy_name
    )

    client.delete_policy_version(policyName=policy_name, policyVersionId="1")
    policy_versions = client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(4)

    client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy1["policyVersionId"]
    )
    policy_versions = client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(3)
    client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy2["policyVersionId"]
    )
    policy_versions = client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(2)

    client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy3["policyVersionId"]
    )
    policy_versions = client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(1)

    # should fail as it"s the default policy. Should use delete_policy instead
    with pytest.raises(ClientError) as exc:
        client.delete_policy_version(
            policyName=policy_name, policyVersionId=policy4["policyVersionId"]
        )
    err = exc.value.response["Error"]
    err["Message"].should.equal("Cannot delete the default version of a policy")


@mock_iot
def test_delete_policy_validation():
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
    client = boto3.client("iot", region_name="ap-northeast-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]
    policy_name = "my-policy"
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_principal_policy(policyName=policy_name, principal=cert_arn)

    with pytest.raises(ClientError) as e:
        client.delete_policy(policyName=policy_name)
    e.value.response["Error"]["Message"].should.contain(
        "The policy cannot be deleted as the policy is attached to one or more principals (name=%s)"
        % policy_name
    )
    res = client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(1)

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    client.delete_policy(policyName=policy_name)
    res = client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(0)


@mock_iot
def test_policy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-policy"
    doc = "{}"
    policy = client.create_policy(policyName=name, policyDocument=doc)
    policy.should.have.key("policyName").which.should.equal(name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(doc)
    policy.should.have.key("policyVersionId").which.should.equal("1")

    policy = client.get_policy(policyName=name)
    policy.should.have.key("policyName").which.should.equal(name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(doc)
    policy.should.have.key("defaultVersionId").which.should.equal("1")

    res = client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(1)
    for policy in res["policies"]:
        policy.should.have.key("policyName").which.should_not.be.none
        policy.should.have.key("policyArn").which.should_not.be.none

    client.delete_policy(policyName=name)
    res = client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(0)
