import boto3
import pytest

from moto import mock_efs


@pytest.fixture(scope="function")
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture(scope="function")
def efs(aws_credentials):  # pylint: disable=unused-argument
    with mock_efs():
        yield boto3.client("efs", region_name="us-east-1")


def test_list_tags_for_resource__without_tags(efs):
    file_system = efs.create_file_system(CreationToken="foobarbaz")
    fs_id = file_system["FileSystemId"]

    resp = efs.list_tags_for_resource(ResourceId=fs_id)
    resp.should.have.key("Tags").equals([])


def test_list_tags_for_resource__with_tags(efs):
    file_system = efs.create_file_system(
        CreationToken="foobarbaz",
        Tags=[{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}],
    )
    fs_id = file_system["FileSystemId"]

    resp = efs.list_tags_for_resource(ResourceId=fs_id)
    resp.should.have.key("Tags").equals(
        [{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}]
    )


def test_tag_resource(efs):
    file_system = efs.create_file_system(
        CreationToken="foobarbaz",
        Tags=[{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}],
    )
    fs_id = file_system["FileSystemId"]

    efs.tag_resource(
        ResourceId=fs_id,
        Tags=[{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}],
    )

    resp = efs.list_tags_for_resource(ResourceId=fs_id)
    resp.should.have.key("Tags").equals(
        [{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}]
    )


def test_untag_resource(efs):
    file_system = efs.create_file_system(
        CreationToken="foobarbaz", Tags=[{"Key": "key1", "Value": "val1"}]
    )
    fs_id = file_system["FileSystemId"]

    efs.tag_resource(
        ResourceId=fs_id,
        Tags=[{"Key": "key2", "Value": "val2"}, {"Key": "key3", "Value": "val3"}],
    )

    efs.untag_resource(ResourceId=fs_id, TagKeys=["key2"])

    resp = efs.list_tags_for_resource(ResourceId=fs_id)
    resp.should.have.key("Tags").equals(
        [{"Key": "key1", "Value": "val1"}, {"Key": "key3", "Value": "val3"}]
    )
