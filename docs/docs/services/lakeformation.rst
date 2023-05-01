.. _implementedservice_lakeformation:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=============
lakeformation
=============

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_lakeformation
            def test_lakeformation_behaviour:
                boto3.client("lakeformation")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_lf_tags_to_resource
- [ ] assume_decorated_role_with_saml
- [X] batch_grant_permissions
- [X] batch_revoke_permissions
- [ ] cancel_transaction
- [ ] commit_transaction
- [ ] create_data_cells_filter
- [X] create_lf_tag
- [ ] delete_data_cells_filter
- [X] delete_lf_tag
- [ ] delete_objects_on_cancel
- [X] deregister_resource
- [X] describe_resource
- [ ] describe_transaction
- [ ] extend_transaction
- [ ] get_data_cells_filter
- [X] get_data_lake_settings
- [ ] get_effective_permissions_for_path
- [X] get_lf_tag
- [ ] get_query_state
- [ ] get_query_statistics
- [ ] get_resource_lf_tags
- [ ] get_table_objects
- [ ] get_temporary_glue_partition_credentials
- [ ] get_temporary_glue_table_credentials
- [ ] get_work_unit_results
- [ ] get_work_units
- [X] grant_permissions
- [X] list_data_cells_filter
  
        This currently just returns an empty list, as the corresponding Create is not yet implemented
        

- [X] list_lf_tags
- [X] list_permissions
  
        No parameters have been implemented yet
        

- [X] list_resources
- [ ] list_table_storage_optimizers
- [ ] list_transactions
- [X] put_data_lake_settings
- [X] register_resource
- [ ] remove_lf_tags_from_resource
- [X] revoke_permissions
- [ ] search_databases_by_lf_tags
- [ ] search_tables_by_lf_tags
- [ ] start_query_planning
- [ ] start_transaction
- [ ] update_data_cells_filter
- [ ] update_lf_tag
- [ ] update_resource
- [ ] update_table_objects
- [ ] update_table_storage_optimizer

