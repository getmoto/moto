from __future__ import unicode_literals

from os import environ
import pytest
import boto3

from moto import mock_efs, mock_ec2
import moto.server as server


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    environ["AWS_ACCESS_KEY_ID"] = "testing"
    environ["AWS_SESSION_TOKEN"] = "testing"
    environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    environ["AWS_SECURITY_TOKEN"] = "testing"


@pytest.fixture(scope="function")
def ec2(aws_credentials):
    with mock_ec2():
        yield boto3.client("ec2", region_name="us-east-1")


@pytest.fixture(scope="function")
def efs(aws_credentials):
    with mock_efs():
        yield boto3.client("efs", region_name="us-east-1")


@pytest.fixture(scope="function")
def client(efs):
    backend = server.create_backend_app("efs")
    test_client = backend.test_client()
    yield test_client


@pytest.fixture(scope="function")
def subnet_id(ec2):
    desc_sn_resp = ec2.describe_subnets()
    subnet = desc_sn_resp["Subnets"][0]
    yield subnet["SubnetId"]


@pytest.fixture(scope="function")
def file_system_id(efs):
    create_fs_resp = efs.create_file_system(CreationToken="foobarbaz", Backup=True)
    create_fs_resp.pop("ResponseMetadata")
    yield create_fs_resp["FileSystemId"]


"""
Test each method current supported to ensure it connects via the server.

NOTE: this does NOT test whether the endpoints are really functioning, just that they
connect and respond. Tests of functionality are contained in `test_file_system` and
`test_mount_target`.
"""


def test_efs_file_system_create(client):
    res = client.post(
        "/2015-02-01/file-systems", json={"CreationToken": "2398asdfkajsdf"}
    )
    assert res.status_code == 201


def test_efs_file_system_describe(client):
    res = client.get("/2015-02-01/file-systems")
    assert res.status_code == 200


def test_efs_file_system_delete(file_system_id, client):
    res = client.delete("/2015-02-01/file-systems/{}".format(file_system_id))
    assert res.status_code == 204


def test_efs_mount_target_create(file_system_id, subnet_id, client):
    res = client.post(
        "/2015-02-01/mount-targets",
        json={"FileSystemId": file_system_id, "SubnetId": subnet_id,},
    )
    assert res.status_code == 200


def test_efs_mount_target_describe(file_system_id, client):
    res = client.get("/2015-02-01/mount-targets?FileSystemId={}".format(file_system_id))
    assert res.status_code == 200


def test_efs_mount_target_delete(efs, file_system_id, subnet_id, client):
    mt_info = efs.create_mount_target(FileSystemId=file_system_id, SubnetId=subnet_id)
    res = client.delete("/2015-02-01/mount-targets/{}".format(mt_info["MountTargetId"]))
    assert res.status_code == 204


def test_efs_describe_backup_policy(file_system_id, client):
    res = client.get("/2015-02-01/file-systems/{}/backup-policy".format(file_system_id))
    assert res.status_code == 200
