from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_get_all_server_certs():
    conn = boto3.client("iam", region_name="us-east-1")

    conn.upload_server_certificate(
        ServerCertificateName="certname",
        CertificateBody="certbody",
        PrivateKey="privatekey",
    )
    certs = conn.list_server_certificates()["ServerCertificateMetadataList"]
    assert len(certs) == 1
    cert1 = certs[0]
    assert cert1["ServerCertificateName"] == "certname"
    assert cert1["Arn"] == f"arn:aws:iam::{ACCOUNT_ID}:server-certificate/certname"


@mock_aws
def test_get_server_cert_doesnt_exist():
    conn = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.get_server_certificate(ServerCertificateName="NonExistant")
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert (
        err["Message"]
        == "The Server Certificate with name NonExistant cannot be found."
    )


@mock_aws
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
    assert cert["CertificateBody"] == "certbody"
    assert "CertificateChain" not in cert
    assert "Tags" not in cert
    metadata = cert["ServerCertificateMetadata"]
    assert metadata["Path"] == "/"
    assert metadata["ServerCertificateName"] == "certname"
    assert metadata["Arn"] == f"arn:aws:iam::{ACCOUNT_ID}:server-certificate/certname"
    assert "ServerCertificateId" in metadata
    assert isinstance(metadata["UploadDate"], datetime)
    assert isinstance(metadata["Expiration"], datetime)


@mock_aws
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
    assert err["Code"] == "NoSuchEntity"
    assert (
        err["Message"] == "The Server Certificate with name certname cannot be found."
    )


@mock_aws
def test_delete_unknown_server_cert():
    conn = boto3.client("iam", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.delete_server_certificate(ServerCertificateName="certname")
    err = ex.value.response["Error"]
    assert err["Code"] == "NoSuchEntity"
    assert (
        err["Message"] == "The Server Certificate with name certname cannot be found."
    )
