import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_iot


@mock_iot
def test_certificate_id_generation_deterministic():
    # Creating the same certificate twice should result in the same certificate ID
    client = boto3.client("iot", region_name="us-east-1")
    cert1 = client.create_keys_and_certificate(setAsActive=False)
    client.delete_certificate(certificateId=cert1["certificateId"])

    cert2 = client.register_certificate(
        certificatePem=cert1["certificatePem"], setAsActive=False
    )
    cert2.should.have.key("certificateId").which.should.equal(cert1["certificateId"])
    client.delete_certificate(certificateId=cert2["certificateId"])


@mock_iot
def test_certs():
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert.should.have.key("certificateArn").which.should_not.be.none
    cert.should.have.key("certificateId").which.should_not.be.none
    cert.should.have.key("certificatePem").which.should_not.be.none
    cert.should.have.key("keyPair")
    cert["keyPair"].should.have.key("PublicKey").which.should_not.be.none
    cert["keyPair"].should.have.key("PrivateKey").which.should_not.be.none
    cert_id = cert["certificateId"]

    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key("certificateDescription")
    cert_desc = cert["certificateDescription"]
    cert_desc.should.have.key("certificateArn").which.should_not.be.none
    cert_desc.should.have.key("certificateId").which.should_not.be.none
    cert_desc.should.have.key("certificatePem").which.should_not.be.none
    cert_desc.should.have.key("validity").which.should_not.be.none
    validity = cert_desc["validity"]
    validity.should.have.key("notBefore").which.should_not.be.none
    validity.should.have.key("notAfter").which.should_not.be.none
    cert_desc.should.have.key("status").which.should.equal("ACTIVE")
    cert_pem = cert_desc["certificatePem"]

    res = client.list_certificates()
    for cert in res["certificates"]:
        cert.should.have.key("certificateArn").which.should_not.be.none
        cert.should.have.key("certificateId").which.should_not.be.none
        cert.should.have.key("status").which.should_not.be.none
        cert.should.have.key("creationDate").which.should_not.be.none

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    cert_desc.should.have.key("status").which.should.equal("REVOKED")

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key("certificates")

    # Test register_certificate flow
    cert = client.register_certificate(certificatePem=cert_pem, setAsActive=True)
    cert.should.have.key("certificateId").which.should_not.be.none
    cert.should.have.key("certificateArn").which.should_not.be.none
    cert_id = cert["certificateId"]

    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(1)
    for cert in res["certificates"]:
        cert.should.have.key("certificateArn").which.should_not.be.none
        cert.should.have.key("certificateId").which.should_not.be.none
        cert.should.have.key("status").which.should_not.be.none
        cert.should.have.key("creationDate").which.should_not.be.none

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    cert_desc.should.have.key("status").which.should.equal("REVOKED")

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key("certificates")

    # Test register_certificate without CA flow
    cert = client.register_certificate_without_ca(
        certificatePem=cert_pem, status="INACTIVE"
    )
    cert.should.have.key("certificateId").which.should_not.be.none
    cert.should.have.key("certificateArn").which.should_not.be.none
    cert_id = cert["certificateId"]

    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(1)
    for cert in res["certificates"]:
        cert.should.have.key("certificateArn").which.should_not.be.none
        cert.should.have.key("certificateId").which.should_not.be.none
        cert.should.have.key("status").which.should_not.be.none
        cert.should.have.key("creationDate").which.should_not.be.none

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key("certificates")


@mock_iot
def test_create_certificate_validation():
    # Test we can't create a cert that already exists
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=False)

    with pytest.raises(ClientError) as e:
        client.register_certificate(
            certificatePem=cert["certificatePem"], setAsActive=False
        )
    e.value.response["Error"]["Message"].should.contain(
        "The certificate is already provisioned or registered"
    )

    with pytest.raises(ClientError) as e:
        client.register_certificate_without_ca(
            certificatePem=cert["certificatePem"], status="ACTIVE"
        )
    e.value.response["Error"]["Message"].should.contain(
        "The certificate is already provisioned or registered"
    )


@mock_iot
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
    e.value.response["Error"]["Message"].should.contain(
        "Certificate must be deactivated (not ACTIVE) before deletion."
    )
    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(1)

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")
    with pytest.raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    e.value.response["Error"]["Message"].should.contain(
        "Things must be detached before deletion (arn: %s)" % cert_arn
    )
    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(1)

    client.detach_thing_principal(thingName=thing_name, principal=cert_arn)
    with pytest.raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    e.value.response["Error"]["Message"].should.contain(
        "Certificate policies must be detached before deletion (arn: %s)" % cert_arn
    )
    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(1)

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(0)


@mock_iot
def test_certs_create_inactive():
    client = boto3.client("iot", region_name="ap-northeast-1")
    cert = client.create_keys_and_certificate(setAsActive=False)
    cert_id = cert["certificateId"]

    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key("certificateDescription")
    cert_desc = cert["certificateDescription"]
    cert_desc.should.have.key("status").which.should.equal("INACTIVE")

    client.update_certificate(certificateId=cert_id, newStatus="ACTIVE")
    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key("certificateDescription")
    cert_desc = cert["certificateDescription"]
    cert_desc.should.have.key("status").which.should.equal("ACTIVE")
