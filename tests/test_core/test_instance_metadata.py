import requests

from moto import mock_ec2, settings

if settings.TEST_SERVER_MODE:
    BASE_URL = "http://localhost:5000"
else:
    BASE_URL = "http://169.254.169.254"


@mock_ec2
def test_latest_meta_data():
    res = requests.get(f"{BASE_URL}/latest/meta-data/")
    assert res.content == b"iam"


@mock_ec2
def test_meta_data_iam():
    res = requests.get(f"{BASE_URL}/latest/meta-data/iam")
    json_response = res.json()
    default_role = json_response["security-credentials"]["default-role"]
    assert "AccessKeyId" in default_role
    assert "SecretAccessKey" in default_role
    assert "Token" in default_role
    assert "Expiration" in default_role


@mock_ec2
def test_meta_data_security_credentials():
    res = requests.get(f"{BASE_URL}/latest/meta-data/iam/security-credentials/")
    assert res.content == b"default-role"


@mock_ec2
def test_meta_data_default_role():
    res = requests.get(
        f"{BASE_URL}/latest/meta-data/iam/security-credentials/default-role"
    )
    json_response = res.json()
    assert "AccessKeyId" in json_response
    assert "SecretAccessKey" in json_response
    assert "Token" in json_response
    assert "Expiration" in json_response
