import pytest
from . import fixture_efs  # noqa # pylint: disable=unused-import


@pytest.fixture(scope="function", name="file_system")
def fixture_file_system(efs):
    create_fs_resp = efs.create_file_system(CreationToken="foobarbaz")
    create_fs_resp.pop("ResponseMetadata")
    yield create_fs_resp


def test_list_tags_for_resource__without_tags(efs, file_system):
    file_system_id = file_system["FileSystemId"]

    ap_id = efs.create_access_point(ClientToken="ct", FileSystemId=file_system_id)[
        "AccessPointId"
    ]

    resp = efs.list_tags_for_resource(ResourceId=ap_id)
    resp.should.have.key("Tags").equals([])


def test_list_tags_for_resource__with_tags(efs, file_system):
    file_system_id = file_system["FileSystemId"]

    ap_id = efs.create_access_point(
        ClientToken="ct",
        Tags=[{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}],
        FileSystemId=file_system_id,
    )["AccessPointId"]

    resp = efs.list_tags_for_resource(ResourceId=ap_id)
    resp.should.have.key("Tags").equals(
        [{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}]
    )


def test_tag_resource(efs, file_system):
    file_system_id = file_system["FileSystemId"]

    ap_id = efs.create_access_point(ClientToken="ct", FileSystemId=file_system_id)[
        "AccessPointId"
    ]

    efs.tag_resource(
        ResourceId=ap_id,
        Tags=[{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}],
    )

    resp = efs.list_tags_for_resource(ResourceId=ap_id)
    resp.should.have.key("Tags").equals(
        [{"Key": "key", "Value": "value"}, {"Key": "Name", "Value": "myname"}]
    )


def test_untag_resource(efs, file_system):
    file_system_id = file_system["FileSystemId"]

    ap_id = efs.create_access_point(
        ClientToken="ct",
        Tags=[{"Key": "key1", "Value": "val1"}],
        FileSystemId=file_system_id,
    )["AccessPointId"]

    efs.tag_resource(
        ResourceId=ap_id,
        Tags=[{"Key": "key2", "Value": "val2"}, {"Key": "key3", "Value": "val3"}],
    )

    efs.untag_resource(ResourceId=ap_id, TagKeys=["key2"])

    resp = efs.list_tags_for_resource(ResourceId=ap_id)
    resp.should.have.key("Tags").equals(
        [{"Key": "key1", "Value": "val1"}, {"Key": "key3", "Value": "val3"}]
    )
