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

            @mock_dynamodb
            def test_dynamodb_behaviour:
                boto3.client("dynamodb")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] batch_execute_statement
  
        Please see the documentation for `execute_statement` to see the limitations of what is supported.
        

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
- [ ] describe_import
- [ ] describe_kinesis_streaming_destination
- [ ] describe_limits
- [X] describe_table
- [ ] describe_table_replica_auto_scaling
- [X] describe_time_to_live
- [ ] disable_kinesis_streaming_destination
- [ ] enable_kinesis_streaming_destination
- [X] execute_statement
  
        Pagination is not yet implemented.

        Parsing is highly experimental - please raise an issue if you find any bugs.
        

- [X] execute_transaction
  
        Please see the documentation for `execute_statement` to see the limitations of what is supported.
        

- [ ] export_table_to_point_in_time
- [X] get_item
- [ ] import_table
- [X] list_backups
- [ ] list_contributor_insights
- [ ] list_exports
- [ ] list_global_tables
- [ ] list_imports
- [X] list_tables
- [X] list_tags_of_resource
- [X] put_item
- [X] query
- [X] restore_table_from_backup
- [X] restore_table_to_point_in_time
  
        Currently this only accepts the source and target table elements, and will
        copy all items from the source without respect to other arguments.
        

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

