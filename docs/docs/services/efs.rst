.. _implementedservice_efs:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
efs
===

.. autoclass:: moto.efs.models.EFSBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_efs
            def test_efs_behaviour:
                boto3.client("efs")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_access_point
- [X] create_file_system
  Create a new EFS File System Volume.

        https://docs.aws.amazon.com/efs/latest/ug/API_CreateFileSystem.html
        

- [X] create_mount_target
  Create a new EFS Mount Target for a given File System to a given subnet.

        Note that you can only create one mount target for each availability zone
        (which is implied by the subnet ID).

        https://docs.aws.amazon.com/efs/latest/ug/API_CreateMountTarget.html
        

- [ ] create_replication_configuration
- [ ] create_tags
- [X] delete_access_point
- [X] delete_file_system
  Delete the file system specified by the given file_system_id.

        Note that mount targets must be deleted first.

        https://docs.aws.amazon.com/efs/latest/ug/API_DeleteFileSystem.html
        

- [ ] delete_file_system_policy
- [X] delete_mount_target
  Delete a mount target specified by the given mount_target_id.

        Note that this will also delete a network interface.

        https://docs.aws.amazon.com/efs/latest/ug/API_DeleteMountTarget.html
        

- [ ] delete_replication_configuration
- [ ] delete_tags
- [X] describe_access_points
  
        Pagination is not yet implemented
        

- [ ] describe_account_preferences
- [X] describe_backup_policy
- [ ] describe_file_system_policy
- [X] describe_file_systems
  Describe all the EFS File Systems, or specific File Systems.

        https://docs.aws.amazon.com/efs/latest/ug/API_DescribeFileSystems.html
        

- [X] describe_lifecycle_configuration
- [X] describe_mount_target_security_groups
- [X] describe_mount_targets
  Describe the mount targets given an access point ID, mount target ID or a file system ID.

        https://docs.aws.amazon.com/efs/latest/ug/API_DescribeMountTargets.html
        

- [ ] describe_replication_configurations
- [ ] describe_tags
- [X] list_tags_for_resource
- [X] modify_mount_target_security_groups
- [ ] put_account_preferences
- [ ] put_backup_policy
- [ ] put_file_system_policy
- [X] put_lifecycle_configuration
- [X] tag_resource
- [X] untag_resource
- [ ] update_file_system

