.. _implementedservice_datasync:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
datasync
========



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_datasync
            def test_datasync_behaviour:
                boto3.client("datasync")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] cancel_task_execution
- [ ] create_agent
- [ ] create_location_efs
- [ ] create_location_fsx_windows
- [ ] create_location_hdfs
- [ ] create_location_nfs
- [ ] create_location_object_storage
- [ ] create_location_s3
- [ ] create_location_smb
- [X] create_task
- [ ] delete_agent
- [X] delete_location
- [X] delete_task
- [ ] describe_agent
- [ ] describe_location_efs
- [ ] describe_location_fsx_windows
- [ ] describe_location_hdfs
- [ ] describe_location_nfs
- [ ] describe_location_object_storage
- [ ] describe_location_s3
- [ ] describe_location_smb
- [ ] describe_task
- [ ] describe_task_execution
- [ ] list_agents
- [ ] list_locations
- [ ] list_tags_for_resource
- [ ] list_task_executions
- [ ] list_tasks
- [X] start_task_execution
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_agent
- [ ] update_location_hdfs
- [ ] update_location_nfs
- [ ] update_location_object_storage
- [ ] update_location_smb
- [X] update_task
- [ ] update_task_execution

