from . import fixture_efs  # noqa # pylint: disable=unused-import


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
