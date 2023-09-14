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
- [ ] batch_get_prepared_statement
- [ ] batch_get_query_execution
- [ ] cancel_capacity_reservation
- [ ] create_capacity_reservation
- [X] create_data_catalog
- [X] create_named_query
- [ ] create_notebook
- [X] create_prepared_statement
- [ ] create_presigned_notebook_url
- [X] create_work_group
- [ ] delete_capacity_reservation
- [ ] delete_data_catalog
- [ ] delete_named_query
- [ ] delete_notebook
- [ ] delete_prepared_statement
- [ ] delete_work_group
- [ ] export_notebook
- [ ] get_calculation_execution
- [ ] get_calculation_execution_code
- [ ] get_calculation_execution_status
- [ ] get_capacity_assignment_configuration
- [ ] get_capacity_reservation
- [X] get_data_catalog
- [ ] get_database
- [X] get_named_query
- [ ] get_notebook_metadata
- [X] get_prepared_statement
- [X] get_query_execution
- [X] get_query_results
  
        Queries are not executed by Moto, so this call will always return 0 rows by default.

        You can use a dedicated API to override this, by configuring a queue of expected results.

        A request to `get_query_results` will take the first result from that queue, and assign it to the provided QueryExecutionId. Subsequent requests using the same QueryExecutionId will return the same result. Other requests using a different QueryExecutionId will take the next result from the queue, or return an empty result if the queue is empty.

        Configuring this queue by making an HTTP request to `/moto-api/static/athena/query-results`. An example invocation looks like this:

        .. sourcecode:: python

            expected_results = {
                "account_id": "123456789012",  # This is the default - can be omitted
                "region": "us-east-1",  # This is the default - can be omitted
                "results": [
                    {
                        "rows": [{"Data": [{"VarCharValue": "1"}]}],
                        "column_info": [{
                            "CatalogName": "string",
                            "SchemaName": "string",
                            "TableName": "string",
                            "Name": "string",
                            "Label": "string",
                            "Type": "string",
                            "Precision": 123,
                            "Scale": 123,
                            "Nullable": "NOT_NULL",
                            "CaseSensitive": True,
                        }],
                    },
                    # other results as required
                ],
            }
            resp = requests.post(
                "http://motoapi.amazonaws.com:5000/moto-api/static/athena/query-results",
                json=expected_results,
            )
            assert resp.status_code == 201

            client = boto3.client("athena", region_name="us-east-1")
            details = client.get_query_execution(QueryExecutionId="any_id")["QueryExecution"]

        .. note:: The exact QueryExecutionId is not relevant here, but will likely be whatever value is returned by start_query_execution

        

- [ ] get_query_runtime_statistics
- [ ] get_session
- [ ] get_session_status
- [ ] get_table_metadata
- [X] get_work_group
- [ ] import_notebook
- [ ] list_application_dpu_sizes
- [ ] list_calculation_executions
- [ ] list_capacity_reservations
- [X] list_data_catalogs
- [ ] list_databases
- [ ] list_engine_versions
- [ ] list_executors
- [X] list_named_queries
- [ ] list_notebook_metadata
- [ ] list_notebook_sessions
- [ ] list_prepared_statements
- [X] list_query_executions
- [ ] list_sessions
- [ ] list_table_metadata
- [ ] list_tags_for_resource
- [X] list_work_groups
- [ ] put_capacity_assignment_configuration
- [ ] start_calculation_execution
- [X] start_query_execution
- [ ] start_session
- [ ] stop_calculation_execution
- [X] stop_query_execution
- [ ] tag_resource
- [ ] terminate_session
- [ ] untag_resource
- [ ] update_capacity_reservation
- [ ] update_data_catalog
- [ ] update_named_query
- [ ] update_notebook
- [ ] update_notebook_metadata
- [ ] update_prepared_statement
- [ ] update_work_group

