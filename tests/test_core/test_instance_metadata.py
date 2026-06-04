import pytest
import requests

from moto import mock_aws, settings

if settings.TEST_SERVER_MODE:
    BASE_URL = "http://localhost:5000"
else:
    BASE_URL = "http://169.254.169.254"


@mock_aws
def test_latest_meta_data() -> None:
    res = requests.get(f"{BASE_URL}/latest/meta-data/")
    assert res.content == b"iam"


@mock_aws
def test_meta_data_iam() -> None:
    res = requests.get(f"{BASE_URL}/latest/meta-data/iam")
    json_response = res.json()
    default_role = json_response["security-credentials"]["default-role"]
    assert "AccessKeyId" in default_role
    assert "SecretAccessKey" in default_role
    assert "Token" in default_role
    assert "Expiration" in default_role


@mock_aws
def test_meta_data_security_credentials() -> None:
    res = requests.get(f"{BASE_URL}/latest/meta-data/iam/security-credentials/")
    assert res.content == b"default-role"


@mock_aws
def test_meta_data_default_role() -> None:
    res = requests.get(
        f"{BASE_URL}/latest/meta-data/iam/security-credentials/default-role"
    )
    json_response = res.json()
    assert "AccessKeyId" in json_response
    assert "SecretAccessKey" in json_response
    assert "Token" in json_response
    assert "Expiration" in json_response


@mock_aws
def test_imdsv2_token() -> None:
    res = requests.put(
        f"{BASE_URL}/latest/api/token",
        headers={"x-aws-ec2-metadata-token-ttl-seconds": "21600"},
    )
    assert res.status_code == 200
    assert res.text == "fake-imdsv2-token"


@mock_aws
def test_imdsv2_flow() -> None:
    token_res = requests.put(
        f"{BASE_URL}/latest/api/token",
        headers={"x-aws-ec2-metadata-token-ttl-seconds": "21600"},
    )
    assert token_res.status_code == 200
    token = token_res.text

    headers = {"x-aws-ec2-metadata-token": token}

    role_res = requests.get(
        f"{BASE_URL}/latest/meta-data/iam/security-credentials/", headers=headers
    )
    assert role_res.status_code == 200
    role = role_res.text

    creds_res = requests.get(
        f"{BASE_URL}/latest/meta-data/iam/security-credentials/{role}", headers=headers
    )
    assert creds_res.status_code == 200
    creds = creds_res.json()
    assert "AccessKeyId" in creds
    assert "SecretAccessKey" in creds


@mock_aws
@pytest.mark.parametrize(
    "path,expected",
    # random collection of metadata paths
    [
        ("instance-id", "i-fake"),
        ("ami-id", "ami-moto-virtual"),
        ("reservation-id", "r-moto-virtual"),
        ("security-groups", "moto-default"),
        ("mac", "00:de:ad:be:ef:00"),
    ],
)
def test_common_metadata_paths(path: str, expected: str) -> None:
    res = requests.get(f"{BASE_URL}/latest/meta-data/{path}")
    assert res.status_code == 200
    assert res.text == expected
