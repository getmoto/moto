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
