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
    assert "ats" not in endpoint["endpointAddress"]
    assert f"iot.{region_name}.amazonaws.com" in endpoint["endpointAddress"]

    # iot:Data-ATS
    endpoint = client.describe_endpoint(endpointType="iot:Data-ATS")
    assert f"ats.iot.{region_name}.amazonaws.com" in endpoint["endpointAddress"]

    # iot:Data-ATS
    endpoint = client.describe_endpoint(endpointType="iot:CredentialProvider")
    assert f"credentials.iot.{region_name}.amazonaws.com" in endpoint["endpointAddress"]

    # iot:Data-ATS
    endpoint = client.describe_endpoint(endpointType="iot:Jobs")
    assert f"jobs.iot.{region_name}.amazonaws.com" in endpoint["endpointAddress"]

    # raise InvalidRequestException
    with pytest.raises(ClientError) as exc:
        client.describe_endpoint(endpointType="iot:Abc")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"


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
    assert len(res["policies"]) == 1
    for policy in res["policies"]:
        assert policy["policyName"] is not None
        assert policy["policyArn"] is not None

    # do nothing if policy have already attached to certificate
    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    assert len(res["policies"]) == 1
    for policy in res["policies"]:
        assert policy["policyName"] is not None
        assert policy["policyArn"] is not None

    res = client.list_policy_principals(policyName=policy_name)
    assert len(res["principals"]) == 1
    assert res["principals"][0].startswith(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/"
    )

    client.detach_policy(policyName=policy_name, target=cert_arn)
    res = client.list_principal_policies(principal=cert_arn)
    assert len(res["policies"]) == 0
    res = client.list_policy_principals(policyName=policy_name)
    assert len(res["principals"]) == 0
    with pytest.raises(ClientError) as e:
        client.detach_policy(policyName=policy_name, target=cert_arn)
    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"


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
    assert len(res["policies"]) == 1
    assert res["policies"][0]["policyName"] == "my-policy"
    assert (
        res["policies"][0]["policyArn"]
        == f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:policy/my-policy"
    )

    res = client.list_policy_principals(policyName=policy_name)
    assert len(res["principals"]) == 1
    assert res["principals"][0].startswith(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/"
    )

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    res = client.list_principal_policies(principal=cert_arn)
    assert len(res["policies"]) == 0
    res = client.list_policy_principals(policyName=policy_name)
    assert len(res["principals"]) == 0


@mock_iot
def test_principal_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "my-thing"
    client.create_thing(thingName=thing_name)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    client.attach_thing_principal(thingName=thing_name, principal=cert_arn)

    res = client.list_principal_things(principal=cert_arn)
    assert len(res["things"]) == 1
    assert res["things"][0] == thing_name
    res = client.list_thing_principals(thingName=thing_name)
    assert len(res["principals"]) == 1
    assert res["principals"][0].startswith(
        f"arn:aws:iot:ap-northeast-1:{ACCOUNT_ID}:cert/"
    )

    client.detach_thing_principal(thingName=thing_name, principal=cert_arn)
    res = client.list_principal_things(principal=cert_arn)
    assert len(res["things"]) == 0
    res = client.list_thing_principals(thingName=thing_name)
    assert len(res["principals"]) == 0

    with pytest.raises(ClientError) as e:
        client.list_thing_principals(thingName="xxx")

    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert (
        e.value.response["Error"]["Message"]
        == "Failed to list principals for thing xxx because the thing does not exist in your account"
    )
