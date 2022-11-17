import sure  # noqa # pylint: disable=unused-import
import boto3

from moto import mock_iot
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from botocore.exceptions import ClientError
import pytest


@mock_iot
def test_endpoints():
    region_name = "ap-northeast-1"
    client = boto3.client("iot", region_name=region_name)

    # iot:Data
    endpoint = client.describe_endpoint(endpointType="iot:Data")
    endpoint.should.have.key("endpointAddress").which.should_not.contain("ats")
    endpoint.should.have.key("endpointAddress").which.should.contain(
        f"iot.{region_name}.amazonaws.com"
    )

    # iot:Data-ATS
    endpoint = client.describe_endpoint(endpointType="iot:Data-ATS")
    endpoint.should.have.key("endpointAddress").which.should.contain(
        f"ats.iot.{region_name}.amazonaws.com"
    )

    # iot:Data-ATS
    endpoint = client.describe_endpoint(endpointType="iot:CredentialProvider")
    endpoint.should.have.key("endpointAddress").which.should.contain(
        f"credentials.iot.{region_name}.amazonaws.com"
    )

    # iot:Data-ATS
    endpoint = client.describe_endpoint(endpointType="iot:Jobs")
    endpoint.should.have.key("endpointAddress").which.should.contain(
        f"jobs.iot.{region_name}.amazonaws.com"
    )

    # raise InvalidRequestException
    try:
        client.describe_endpoint(endpointType="iot:Abc")
    except client.exceptions.InvalidRequestException as exc:
        error_code = exc.response["Error"]["Code"]
        error_code.should.equal("InvalidRequestException")
    else:
        raise Exception("Should have raised error")


@mock_iot
def test_principal_policy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    policy_name = "my-policy"
    doc = "{}"
    client.create_policy(policyName=policy_name, policyDocument=doc)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    for policy in res["policies"]:
        policy.should.have.key("policyName").which.should_not.be.none
        policy.should.have.key("policyArn").which.should_not.be.none

    # do nothing if policy have already attached to certificate
    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    for policy in res["policies"]:
        policy.should.have.key("policyName").which.should_not.be.none
        policy.should.have.key("policyArn").which.should_not.be.none

    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key("principals").length_of(1)
    res["principals"][0].should.match(f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/")

    client.detach_policy(policyName=policy_name, target=cert_arn)
    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(0)
    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key("principals").which.should.have.length_of(0)
    with pytest.raises(ClientError) as e:
        client.detach_policy(policyName=policy_name, target=cert_arn)
    e.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_iot
def test_principal_policy_deprecated():
    client = boto3.client("iot", region_name="ap-northeast-1")
    policy_name = "my-policy"
    doc = "{}"
    client.create_policy(policyName=policy_name, policyDocument=doc)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    client.attach_principal_policy(policyName=policy_name, principal=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key("policies").length_of(1)
    res["policies"][0].should.have.key("policyName").equal("my-policy")
    res["policies"][0].should.have.key("policyArn").equal(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:policy/my-policy"
    )

    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key("principals").length_of(1)
    res["principals"][0].should.match(f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/")

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(0)
    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key("principals").which.should.have.length_of(0)


@mock_iot
def test_principal_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "my-thing"
    client.create_thing(thingName=thing_name)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    client.attach_thing_principal(thingName=thing_name, principal=cert_arn)

    res = client.list_principal_things(principal=cert_arn)
    res.should.have.key("things").which.should.have.length_of(1)
    res["things"][0].should.equal(thing_name)
    res = client.list_thing_principals(thingName=thing_name)
    res.should.have.key("principals").length_of(1)
    res["principals"][0].should.match(f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/")

    client.detach_thing_principal(thingName=thing_name, principal=cert_arn)
    res = client.list_principal_things(principal=cert_arn)
    res.should.have.key("things").which.should.have.length_of(0)
    res = client.list_thing_principals(thingName=thing_name)
    res.should.have.key("principals").which.should.have.length_of(0)

    with pytest.raises(ClientError) as e:
        client.list_thing_principals(thingName="xxx")

    e.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    e.value.response["Error"]["Message"].should.equal(
        "Failed to list principals for thing xxx because the thing does not exist in your account"
    )
