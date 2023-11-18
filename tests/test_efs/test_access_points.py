import pytest
from botocore.exceptions import ClientError

from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from . import fixture_efs  # noqa # pylint: disable=unused-import


@pytest.fixture(scope="function", name="file_system")
def fixture_file_system(efs):
    create_fs_resp = efs.create_file_system(CreationToken="foobarbaz")
    create_fs_resp.pop("ResponseMetadata")
    yield create_fs_resp


def test_describe_access_points__initial(efs):
    resp = efs.describe_access_points()
    assert resp["AccessPoints"] == []


def test_create_access_point__simple(efs, file_system):
    fs_id = file_system["FileSystemId"]

    resp = efs.create_access_point(ClientToken="ct", FileSystemId=fs_id)
    assert resp["ClientToken"] == "ct"
    assert "AccessPointId" in resp
    assert "AccessPointArn" in resp
    assert resp["FileSystemId"] == fs_id
    assert resp["OwnerId"] == ACCOUNT_ID
    assert resp["LifeCycleState"] == "available"

    assert resp["RootDirectory"] == {"Path": "/"}


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

    assert resp["ClientToken"] == "ct"
    assert resp["Name"] == "myname"
    assert resp["Tags"] == [
        {"Key": "key", "Value": "value"},
        {"Key": "Name", "Value": "myname"},
    ]
    assert "AccessPointId" in resp
    assert "AccessPointArn" in resp
    assert resp["FileSystemId"] == fs_id
    assert resp["PosixUser"] == {"Uid": 123, "Gid": 123, "SecondaryGids": [124, 125]}
    assert resp["RootDirectory"] == {
        "Path": "/root/path",
        "CreationInfo": {
            "OwnerUid": 987,
            "OwnerGid": 986,
            "Permissions": "root_permissions",
        },
    }
    assert resp["OwnerId"] == ACCOUNT_ID
    assert resp["LifeCycleState"] == "available"


def test_describe_access_point(efs, file_system):
    fs_id = file_system["FileSystemId"]

    access_point_id = efs.create_access_point(ClientToken="ct", FileSystemId=fs_id)[
        "AccessPointId"
    ]

    resp = efs.describe_access_points(AccessPointId=access_point_id)
    assert len(resp["AccessPoints"]) == 1
    access_point = resp["AccessPoints"][0]

    assert access_point["ClientToken"] == "ct"
    assert "AccessPointId" in access_point
    assert "AccessPointArn" in access_point
    assert access_point["FileSystemId"] == fs_id
    assert access_point["OwnerId"] == ACCOUNT_ID
    assert access_point["LifeCycleState"] == "available"


def test_describe_access_points__multiple(efs, file_system):
    fs_id = file_system["FileSystemId"]

    efs.create_access_point(ClientToken="ct1", FileSystemId=fs_id)
    efs.create_access_point(ClientToken="ct2", FileSystemId=fs_id)

    resp = efs.describe_access_points()
    assert len(resp["AccessPoints"]) == 2


def test_describe_access_points__filters(efs):
    fs_id1 = efs.create_file_system(CreationToken="foobarbaz")["FileSystemId"]
    fs_id2 = efs.create_file_system(CreationToken="bazbarfoo")["FileSystemId"]

    ap_id1 = efs.create_access_point(ClientToken="ct", FileSystemId=fs_id1)[
        "AccessPointId"
    ]
    ap_id2 = efs.create_access_point(ClientToken="ct", FileSystemId=fs_id2)[
        "AccessPointId"
    ]

    resp = efs.describe_access_points(FileSystemId=fs_id1)
    assert len(resp["AccessPoints"]) == 1
    assert resp.get("NextToken") is None
    assert resp["AccessPoints"][0]["FileSystemId"] == fs_id1
    assert resp["AccessPoints"][0]["AccessPointId"] == ap_id1

    resp = efs.describe_access_points(AccessPointId=ap_id2)
    assert len(resp["AccessPoints"]) == 1
    assert resp.get("NextToken") is None
    assert resp["AccessPoints"][0]["FileSystemId"] == fs_id2
    assert resp["AccessPoints"][0]["AccessPointId"] == ap_id2


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
    assert len(resp["AccessPoints"]) == 1

    # The first one still exists
    efs.describe_access_points(AccessPointId=ap_id1)

    # The second one is gone
    with pytest.raises(ClientError) as exc_info:
        efs.describe_access_points(AccessPointId=ap_id2)
    err = exc_info.value.response["Error"]
    assert err["Code"] == "AccessPointNotFound"
