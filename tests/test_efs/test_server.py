import re
import pytest

from moto import mock_efs, mock_ec2
import moto.server as server


FILE_SYSTEMS = "/2015-02-01/file-systems"
MOUNT_TARGETS = "/2015-02-01/mount-targets"


@pytest.fixture(scope="function", name="aws_credentials")
def fixture_aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture(scope="function", name="efs_client")
def fixture_efs_client(aws_credentials):  # pylint: disable=unused-argument
    with mock_efs():
        yield server.create_backend_app("efs").test_client()


@pytest.fixture(scope="function", name="subnet_id")
def fixture_subnet_id(aws_credentials):  # pylint: disable=unused-argument
    with mock_ec2():
        ec2_client = server.create_backend_app("ec2").test_client()
        resp = ec2_client.get("/?Action=DescribeSubnets")
        subnet_ids = re.findall("<subnetId>(.*?)</subnetId>", resp.data.decode("utf-8"))
        yield subnet_ids[0]


@pytest.fixture(scope="function", name="file_system_id")
def fixture_file_system_id(efs_client):
    resp = efs_client.post(
        FILE_SYSTEMS, json={"CreationToken": "foobarbaz", "Backup": True}
    )
    yield resp.json["FileSystemId"]


"""
Test each method current supported to ensure it connects via the server.

NOTE: this does NOT test whether the endpoints are really functioning, just that they
connect and respond. Tests of functionality are contained in `test_file_system` and
`test_mount_target`.
"""


def test_efs_file_system_create(efs_client):
    res = efs_client.post(FILE_SYSTEMS, json={"CreationToken": "2398asdfkajsdf"})
    assert res.status_code == 201


def test_efs_file_system_describe(efs_client):
    res = efs_client.get(FILE_SYSTEMS)
    assert res.status_code == 200


def test_efs_file_system_delete(file_system_id, efs_client):
    res = efs_client.delete(f"/2015-02-01/file-systems/{file_system_id}")
    assert res.status_code == 204


def test_efs_mount_target_create(file_system_id, subnet_id, efs_client):
    res = efs_client.post(
        "/2015-02-01/mount-targets",
        json={"FileSystemId": file_system_id, "SubnetId": subnet_id},
    )
    assert res.status_code == 200


def test_efs_mount_target_describe(file_system_id, efs_client):
    res = efs_client.get(f"/2015-02-01/mount-targets?FileSystemId={file_system_id}")
    assert res.status_code == 200


def test_efs_mount_target_delete(file_system_id, subnet_id, efs_client):
    create_res = efs_client.post(
        "/2015-02-01/mount-targets",
        json={"FileSystemId": file_system_id, "SubnetId": subnet_id},
    )
    mt_id = create_res.json["MountTargetId"]
    res = efs_client.delete(f"/2015-02-01/mount-targets/{mt_id}")
    assert res.status_code == 204


def test_efs_describe_backup_policy(file_system_id, efs_client):
    res = efs_client.get(f"/2015-02-01/file-systems/{file_system_id}/backup-policy")
    assert res.status_code == 200
