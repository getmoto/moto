import pytest
from botocore.exceptions import ClientError

from . import fixture_efs  # noqa # pylint: disable=unused-import


def test_describe_filesystem_config__unknown(efs):
    with pytest.raises(ClientError) as exc_info:
        efs.describe_lifecycle_configuration(FileSystemId="unknown")
    err = exc_info.value.response["Error"]
    err["Code"].should.equal("FileSystemNotFound")
    err["Message"].should.equal("File system unknown does not exist.")


def test_describe_filesystem_config__initial(efs):
    create_fs_resp = efs.create_file_system(CreationToken="foobar")
    fs_id = create_fs_resp["FileSystemId"]

    resp = efs.describe_lifecycle_configuration(FileSystemId=fs_id)
    resp.should.have.key("LifecyclePolicies").equals([])


def test_put_lifecycle_configuration(efs):
    # Create the file system.
    create_fs_resp = efs.create_file_system(CreationToken="foobar")
    create_fs_resp.pop("ResponseMetadata")
    fs_id = create_fs_resp["FileSystemId"]

    # Create the lifecycle configuration
    resp = efs.put_lifecycle_configuration(
        FileSystemId=fs_id, LifecyclePolicies=[{"TransitionToIA": "AFTER_30_DAYS"}]
    )
    resp.should.have.key("LifecyclePolicies").length_of(1)
    resp["LifecyclePolicies"][0].should.equal({"TransitionToIA": "AFTER_30_DAYS"})

    # Describe the lifecycle configuration
    resp = efs.describe_lifecycle_configuration(FileSystemId=fs_id)
    resp.should.have.key("LifecyclePolicies").length_of(1)
    resp["LifecyclePolicies"][0].should.equal({"TransitionToIA": "AFTER_30_DAYS"})
