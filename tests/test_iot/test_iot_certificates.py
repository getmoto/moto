import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_certificate_id_generation_deterministic():
    # Creating the same certificate twice should result in the same certificate ID
    client = boto3.client("iot", region_name="us-east-1")
    cert1 = client.create_keys_and_certificate(setAsActive=False)
    client.delete_certificate(certificateId=cert1["certificateId"])

    cert2 = client.register_certificate(
        certificatePem=cert1["certificatePem"], setAsActive=False
    )
    assert cert2["certificateId"] == cert1["certificateId"]
    client.delete_certificate(certificateId=cert2["certificateId"])


@mock_aws
def test_create_certificate_from_csr():
    csr = "-----BEGIN CERTIFICATE REQUEST-----\nMIICijCCAXICAQAwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgTClNvbWUtU3RhdGUx\nITAfBgNVBAoTGEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDCCASIwDQYJKoZIhvcN\nAQEBBQADggEPADCCAQoCggEBAMSUg2mO7mYnhvYUB55K0/ay9WLLgPjOHnbduyCv\nN+udkJaZc+A65ux9LvVo33VHDTlV2Ms9H/42on902WtuS3BNuxdXfD068CpN2lb6\nbSAeuKc6Fdu4BIP2bFYKCyejqBoOmTEhYA8bOM1Wu/pRsq1PkAmcGkvw3mlRx45E\nB2LRicWcg3YEleEBGyLYohyeMu0pnlsc7zsu5T4bwrjetdbDPVbzgu0Mf/evU9hJ\nG/IisXNxQhzPh/DTQsKZSNddZ4bmkAQrRN1nmNXD6QoxBiVyjjgKGrPnX+hz4ugm\naaN9CsOO/cad1E3C0KiI0BQCjxRb80wOpI4utz4pEcY97sUCAwEAAaAAMA0GCSqG\nSIb3DQEBBQUAA4IBAQC64L4JHvwxdxmnXT9Lv12p5CGx99d7VOXQXy29b1yH9cJ+\nFaQ2TH377uOdorSCS4bK7eje9/HLsCNgqftR0EruwSNnukF695BWN8e/AJSZe0vA\n3J/llZ6G7MWuOIhCswsOxqNnM1htu3o6ujXVrgBMeMgQy2tfylWfI7SGR6UmtLYF\nZrPaqXdkpt47ROJNCm2Oht1B0J3QEOmbIp/2XMxrfknzwH6se/CjuliiXVPYxrtO\n5hbZcRqjhugb8FWtaLirqh3Q3+1UIJ+CW0ZczsblP7DNdqqt8YQZpWVIqR64mSXV\nAjq/cupsJST9fey8chcNSTt4nKxOGs3OgXu1ftgy\n-----END CERTIFICATE REQUEST-----\n"
    client = boto3.client("iot", region_name="us-east-2")

    resp = client.create_certificate_from_csr(certificateSigningRequest=csr)
    assert "certificateArn" in resp
    assert "certificateId" in resp
    assert "certificatePem" in resp

    # Can create certificate a second time
    client.create_certificate_from_csr(certificateSigningRequest=csr)

    assert len(client.list_certificates()["certificates"]) == 2


@mock_aws
def test_create_key_and_certificate():
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    assert cert["certificateArn"] is not None
    assert cert["certificateId"] is not None
    assert cert["certificatePem"].startswith("-----BEGIN CERTIFICATE-----")
    assert cert["keyPair"]["PublicKey"].startswith("-----BEGIN PUBLIC KEY-----")
    assert cert["keyPair"]["PrivateKey"].startswith("-----BEGIN RSA PRIVATE KEY-----")


@mock_aws
def test_describe_certificate_by_id():
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_id = cert["certificateId"]

    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    assert cert_desc["certificateArn"] is not None
    assert cert_desc["certificateId"] is not None
    assert cert_desc["certificatePem"] is not None
    assert cert_desc["validity"] is not None
    validity = cert_desc["validity"]
    assert validity["notBefore"] is not None
    assert validity["notAfter"] is not None
    assert cert_desc["status"] == "ACTIVE"


@mock_aws
def test_list_certificates():
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_id = cert["certificateId"]

    res = client.list_certificates()
    for cert in res["certificates"]:
        assert cert["certificateArn"] is not None
        assert cert["certificateId"] is not None
        assert cert["status"] is not None
        assert cert["creationDate"] is not None

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    assert cert_desc["status"] == "REVOKED"


@mock_aws
def test_update_certificate():
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_id = cert["certificateId"]

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    assert cert_desc["status"] == "REVOKED"


@pytest.mark.parametrize("status", ["REVOKED", "INACTIVE"])
@mock_aws
def test_delete_certificate_with_status(status):
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_id = cert["certificateId"]

    # Ensure certificate has the right status before we can delete
    client.update_certificate(certificateId=cert_id, newStatus=status)

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    assert res["certificates"] == []


@mock_aws
def test_register_certificate_without_ca():
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_id = cert["certificateId"]
    cert_pem = cert["certificatePem"]

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")
    client.delete_certificate(certificateId=cert_id)

    # Test register_certificate without CA flow
    cert = client.register_certificate_without_ca(
        certificatePem=cert_pem, status="INACTIVE"
    )
    assert cert["certificateId"] is not None
    assert cert["certificateArn"] is not None
    cert_id = cert["certificateId"]

    res = client.list_certificates()
    assert len(res["certificates"]) == 1
    for cert in res["certificates"]:
        assert cert["certificateArn"] is not None
        assert cert["certificateId"] is not None
        assert cert["status"] is not None
        assert cert["creationDate"] is not None

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    assert "certificates" in res


@mock_aws
def test_create_certificate_validation():
    # Test we can't create a cert that already exists
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=False)

    with pytest.raises(ClientError) as e:
        client.register_certificate(
            certificatePem=cert["certificatePem"], setAsActive=False
        )
    assert (
        "The certificate is already provisioned or registered"
        in e.value.response["Error"]["Message"]
    )

    with pytest.raises(ClientError) as e:
        client.register_certificate_without_ca(
            certificatePem=cert["certificatePem"], status="ACTIVE"
        )
    assert e.value.response["resourceArn"] == cert["certificateArn"]
    assert e.value.response["resourceId"] == cert["certificateId"]
    assert (
        "The certificate is already provisioned or registered"
        in e.value.response["Error"]["Message"]
    )


@mock_aws
def test_delete_certificate_validation():
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
    cert_id = cert["certificateId"]
    cert_arn = cert["certificateArn"]
    policy_name = "my-policy"
    thing_name = "thing-1"
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_principal_policy(policyName=policy_name, principal=cert_arn)
    client.create_thing(thingName=thing_name)
    client.attach_thing_principal(thingName=thing_name, principal=cert_arn)

    with pytest.raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    assert (
        "Certificate must be deactivated (not ACTIVE) before deletion."
        in e.value.response["Error"]["Message"]
    )
    res = client.list_certificates()
    assert len(res["certificates"]) == 1

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")
    with pytest.raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    assert (
        f"Things must be detached before deletion (arn: {cert_arn})"
        in e.value.response["Error"]["Message"]
    )
    res = client.list_certificates()
    assert len(res["certificates"]) == 1

    client.detach_thing_principal(thingName=thing_name, principal=cert_arn)
    with pytest.raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    assert (
        f"Certificate policies must be detached before deletion (arn: {cert_arn})"
        in e.value.response["Error"]["Message"]
    )
    res = client.list_certificates()
    assert len(res["certificates"]) == 1

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    assert len(res["certificates"]) == 0


@mock_aws
def test_delete_certificate_force():
    policy_name = "my-policy"
    client = boto3.client("iot", "us-east-1")
    client.create_policy(policyName=policy_name, policyDocument="doc")

    cert_arn = client.create_keys_and_certificate(setAsActive=True)["certificateArn"]
    cert_id = cert_arn.split("/")[-1]

    client.attach_policy(policyName=policy_name, target=cert_arn)

    # Forced deletion does not work if the status is ACTIVE
    with pytest.raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id, forceDelete=True)
    err = e.value.response["Error"]
    assert "Certificate must be deactivated" in err["Message"]

    client.update_certificate(certificateId=cert_id, newStatus="INACTIVE")
    # If does work if the status is INACTIVE, even though we still have policies attached
    client.delete_certificate(certificateId=cert_id, forceDelete=True)

    res = client.list_certificates()
    assert len(res["certificates"]) == 0


@mock_aws
def test_delete_thing_with_certificate_validation():
    client = boto3.client("iot", region_name="ap-northeast-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_id = cert["certificateId"]
    cert_arn = cert["certificateArn"]
    thing_name = "thing-1"
    client.create_thing(thingName=thing_name)
    client.attach_thing_principal(thingName=thing_name, principal=cert_arn)

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")

    with pytest.raises(ClientError) as e:
        client.delete_thing(thingName=thing_name)
    err = e.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert (
        err["Message"]
        == f"Cannot delete. Thing {thing_name} is still attached to one or more principals"
    )

    client.detach_thing_principal(thingName=thing_name, principal=cert_arn)

    client.delete_thing(thingName=thing_name)

    # Certificate still exists
    res = client.list_certificates()
    assert len(res["certificates"]) == 1
    assert res["certificates"][0]["certificateArn"] == cert_arn
    assert res["certificates"][0]["status"] == "REVOKED"


@mock_aws
def test_certs_create_inactive():
    client = boto3.client("iot", region_name="ap-northeast-1")
    cert = client.create_keys_and_certificate(setAsActive=False)
    cert_id = cert["certificateId"]

    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    assert cert_desc["status"] == "INACTIVE"

    client.update_certificate(certificateId=cert_id, newStatus="ACTIVE")
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    assert cert_desc["status"] == "ACTIVE"
