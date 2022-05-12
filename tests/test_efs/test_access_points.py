import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_efs
from moto.core import ACCOUNT_ID


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


@pytest.fixture(scope="function")
def file_system(efs):
    create_fs_resp = efs.create_file_system(CreationToken="foobarbaz")
    create_fs_resp.pop("ResponseMetadata")
    yield create_fs_resp


def test_describe_access_points__initial(efs):
    resp = efs.describe_access_points()
    resp.should.have.key("AccessPoints").equals([])


def test_create_access_point__simple(efs, file_system):
    fs_id = file_system["FileSystemId"]

    resp = efs.create_access_point(ClientToken="ct", FileSystemId=fs_id)
    resp.should.have.key("ClientToken").equals("ct")
    resp.should.have.key("AccessPointId")
    resp.should.have.key("AccessPointArn")
    resp.should.have.key("FileSystemId").equals(fs_id)
    resp.should.have.key("OwnerId").equals(ACCOUNT_ID)
    resp.should.have.key("LifeCycleState").equals("available")

    resp.should.have.key("RootDirectory").equals({"Path": "/"})


def test_create_access_point__full(efs, file_system):
    fs_id = file_system["FileSystemId"]

    resp = efs.create_access_point(
        ClientToken="ct",
        Tags=[{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}],
        FileSystemId=fs_id,
        PosixUser={"Uid": 123, "Gid": 123, "SecondaryGids": [124, 125]},
        RootDirectory={
            "Path": "/root/path",
            "CreationInfo": {
                "OwnerUid": 987,
                "OwnerGid": 986,
                "Permissions": "root_permissions",
            },
        },
    )

    resp.should.have.key("ClientToken").equals("ct")
    resp.should.have.key("Name").equals("myname")
    resp.should.have.key("Tags").equals(
        [{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}]
    )
    resp.should.have.key("AccessPointId")
    resp.should.have.key("AccessPointArn")
    resp.should.have.key("FileSystemId").equals(fs_id)
    resp.should.have.key("PosixUser").equals(
        {"Uid": 123, "Gid": 123, "SecondaryGids": [124, 125]}
    )
    resp.should.have.key("RootDirectory").equals(
        {
            "Path": "/root/path",
            "CreationInfo": {
                "OwnerUid": 987,
                "OwnerGid": 986,
                "Permissions": "root_permissions",
            },
        }
    )
    resp.should.have.key("OwnerId").equals(ACCOUNT_ID)
    resp.should.have.key("LifeCycleState").equals("available")


def test_describe_access_point(efs, file_system):
    fs_id = file_system["FileSystemId"]

    access_point_id = efs.create_access_point(ClientToken="ct", FileSystemId=fs_id)[
        "AccessPointId"
    ]

    resp = efs.describe_access_points(AccessPointId=access_point_id)
    resp.should.have.key("AccessPoints").length_of(1)
    access_point = resp["AccessPoints"][0]

    access_point.should.have.key("ClientToken").equals("ct")
    access_point.should.have.key("AccessPointId")
    access_point.should.have.key("AccessPointArn")
    access_point.should.have.key("FileSystemId").equals(fs_id)
    access_point.should.have.key("OwnerId").equals(ACCOUNT_ID)
    access_point.should.have.key("LifeCycleState").equals("available")


def test_describe_access_points__multiple(efs, file_system):
    fs_id = file_system["FileSystemId"]

    efs.create_access_point(ClientToken="ct1", FileSystemId=fs_id)
    efs.create_access_point(ClientToken="ct2", FileSystemId=fs_id)

    resp = efs.describe_access_points()
    resp.should.have.key("AccessPoints").length_of(2)


def test_delete_access_points(efs, file_system):
    fs_id = file_system["FileSystemId"]

    ap_id1 = efs.create_access_point(ClientToken="ct1", FileSystemId=fs_id)[
        "AccessPointId"
    ]
    ap_id2 = efs.create_access_point(ClientToken="ct2", FileSystemId=fs_id)[
        "AccessPointId"
    ]

    # Delete one access point
    efs.delete_access_point(AccessPointId=ap_id2)

    # We can only find one
    resp = efs.describe_access_points()
    resp.should.have.key("AccessPoints").length_of(1)

    # The first one still exists
    efs.describe_access_points(AccessPointId=ap_id1)

    # The second one is gone
    with pytest.raises(ClientError) as exc_info:
        efs.describe_access_points(AccessPointId=ap_id2)
    err = exc_info.value.response["Error"]
    err["Code"].should.equal("AccessPointNotFound")
