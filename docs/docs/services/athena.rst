.. _implementedservice_athena:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

======
athena
======

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_athena
            def test_athena_behaviour:
                boto3.client("athena")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] batch_get_named_query
- [ ] batch_get_query_execution
- [X] create_data_catalog
- [X] create_named_query
- [ ] create_prepared_statement
- [X] create_work_group
- [ ] delete_data_catalog
- [ ] delete_named_query
- [ ] delete_prepared_statement
- [ ] delete_work_group
- [X] get_data_catalog
- [ ] get_database
- [X] get_named_query
- [ ] get_prepared_statement
- [ ] get_query_execution
- [ ] get_query_results
- [ ] get_table_metadata
- [X] get_work_group
- [X] list_data_catalogs
- [ ] list_databases
- [ ] list_engine_versions
- [ ] list_named_queries
- [ ] list_prepared_statements
- [ ] list_query_executions
- [ ] list_table_metadata
- [ ] list_tags_for_resource
- [X] list_work_groups
- [X] start_query_execution
- [X] stop_query_execution
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_data_catalog
- [ ] update_named_query
- [ ] update_prepared_statement
- [ ] update_work_group

