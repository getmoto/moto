import boto3
import pytest
import sure  # noqa

from botocore.exceptions import ClientError
from datetime import datetime

from moto import mock_iam
from moto.core import ACCOUNT_ID


@mock_iam
def test_get_all_server_certs():
    conn = boto3.client("iam", region_name="us-east-1")

    conn.upload_server_certificate(
        ServerCertificateName="certname",
        CertificateBody="certbody",
        PrivateKey="privatekey",
    )
    certs = conn.list_server_certificates()["ServerCertificateMetadataList"]
    certs.should.have.length_of(1)
    cert1 = certs[0]
    cert1["ServerCertificateName"].should.equal("certname")
    cert1["Arn"].should.equal(
        "arn:aws:iam::{}:server-certificate/certname".format(ACCOUNT_ID)
    )


@mock_iam
def test_get_server_cert_doesnt_exist():
    conn = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.get_server_certificate(ServerCertificateName="NonExistant")
    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchEntity")
    err["Message"].should.equal(
        "The Server Certificate with name NonExistant cannot be found."
    )


@mock_iam
def test_get_server_cert():
    conn = boto3.client("iam", region_name="us-east-1")

    conn.upload_server_certificate(
        ServerCertificateName="certname",
        CertificateBody="certbody",
        PrivateKey="privatekey",
    )
    cert = conn.get_server_certificate(ServerCertificateName="certname")[
        "ServerCertificate"
    ]
    cert["CertificateBody"].should.equal("certbody")
    cert.shouldnt.have.key("CertificateChain")
    cert.shouldnt.have.key("Tags")
    metadata = cert["ServerCertificateMetadata"]
    metadata["Path"].should.equal("/")
    metadata["ServerCertificateName"].should.equal("certname")
    metadata["Arn"].should.equal(
        "arn:aws:iam::{}:server-certificate/certname".format(ACCOUNT_ID)
    )
    metadata.should.have.key("ServerCertificateId")
    metadata["UploadDate"].should.be.a(datetime)
    metadata["Expiration"].should.be.a(datetime)


@mock_iam
def test_delete_server_cert():
    conn = boto3.client("iam", region_name="us-east-1")

    conn.upload_server_certificate(
        ServerCertificateName="certname",
        CertificateBody="certbody",
        PrivateKey="privatekey",
    )
    conn.get_server_certificate(ServerCertificateName="certname")
    conn.delete_server_certificate(ServerCertificateName="certname")

    with pytest.raises(ClientError) as ex:
        conn.get_server_certificate(ServerCertificateName="certname")
    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchEntity")
    err["Message"].should.equal(
        "The Server Certificate with name certname cannot be found."
    )


@mock_iam
def test_delete_unknown_server_cert():
    conn = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.delete_server_certificate(ServerCertificateName="certname")
    err = ex.value.response["Error"]
    err["Code"].should.equal("NoSuchEntity")
    err["Message"].should.equal(
        "The Server Certificate with name certname cannot be found."
    )
