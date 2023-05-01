.. _implementedservice_timestream-write:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

================
timestream-write
================

.. autoclass:: moto.timestreamwrite.models.TimestreamWriteBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_timestreamwrite
            def test_timestreamwrite_behaviour:
                boto3.client("timestream-write")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] create_batch_load_task
- [X] create_database
- [X] create_table
- [X] delete_database
- [X] delete_table
- [ ] describe_batch_load_task
- [X] describe_database
- [X] describe_endpoints
- [X] describe_table
- [ ] list_batch_load_tasks
- [X] list_databases
- [X] list_tables
- [X] list_tags_for_resource
- [ ] resume_batch_load_task
- [X] tag_resource
- [X] untag_resource
- [X] update_database
- [X] update_table
- [X] write_records

