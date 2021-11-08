.. _implementedservice_dynamodb:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
dynamodb
========



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_dynamodb2
            def test_dynamodb_behaviour:
                boto3.client("dynamodb")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] batch_execute_statement
- [X] batch_get_item
- [X] batch_write_item
- [X] create_backup
- [ ] create_global_table
- [X] create_table
- [X] delete_backup
- [X] delete_item
- [X] delete_table
- [X] describe_backup
- [X] describe_continuous_backups
- [ ] describe_contributor_insights
- [X] describe_endpoints
- [ ] describe_export
- [ ] describe_global_table
- [ ] describe_global_table_settings
- [ ] describe_kinesis_streaming_destination
- [ ] describe_limits
- [X] describe_table
- [ ] describe_table_replica_auto_scaling
- [X] describe_time_to_live
- [ ] disable_kinesis_streaming_destination
- [ ] enable_kinesis_streaming_destination
- [ ] execute_statement
- [ ] execute_transaction
- [ ] export_table_to_point_in_time
- [X] get_item
- [X] list_backups
- [ ] list_contributor_insights
- [ ] list_exports
- [ ] list_global_tables
- [X] list_tables
- [X] list_tags_of_resource
- [X] put_item
- [X] query
- [X] restore_table_from_backup
- [ ] restore_table_to_point_in_time
- [X] scan
- [X] tag_resource
- [X] transact_get_items
- [X] transact_write_items
- [X] untag_resource
- [X] update_continuous_backups
- [ ] update_contributor_insights
- [ ] update_global_table
- [ ] update_global_table_settings
- [X] update_item
- [X] update_table
- [ ] update_table_replica_auto_scaling
- [X] update_time_to_live

