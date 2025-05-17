import pytest
from botocore.exceptions import ClientError

from . import fixture_efs  # noqa


def test_describe_file_system_policy__initial(efs):
    create_fs_resp = efs.create_file_system(CreationToken="foobar")
    fs_id = create_fs_resp["FileSystemId"]

    with pytest.raises(ClientError) as exc_info:
        efs.describe_file_system_policy(FileSystemId=fs_id)
    err = exc_info.value.response["Error"]
    assert err["Code"] == "PolicyNotFound"


def test_put_file_system_policy(efs):
    # Create the file system.
    create_fs_resp = efs.create_file_system(CreationToken="foobar")
    create_fs_resp.pop("ResponseMetadata")
    fs_id = create_fs_resp["FileSystemId"]

    # Create the filesystem policy
    policy = '{\n  "Version" : "2012-10-17",\n  "Id" : "efs-policy-1234",\n  "Statement" : [ {\n    "Sid" : "efs-statement-1234",\n    "Effect" : "Allow",\n    "Principal" : {\n      "AWS" : "*"\n    },\n    "Action" : [ "elasticfilesystem:ClientRootAccess", "elasticfilesystem:ClientWrite" ],\n    "Resource" : "arn:aws:elasticfilesystem:us-east-1:1234:file-system/fs-1234",\n    "Condition" : {\n      "Bool" : {\n        "elasticfilesystem:AccessedViaMountTarget" : "true"\n      }\n    }\n  } ]\n}'
    resp = efs.put_file_system_policy(FileSystemId=fs_id, Policy=policy)
    assert len(resp["Policy"]) > 1
    assert "ClientRootAccess" in resp["Policy"]

    # Describe the filesystem policy
    resp = efs.describe_file_system_policy(FileSystemId=fs_id)
    assert len(resp["Policy"]) > 1
    assert "ClientRootAccess" in resp["Policy"]
