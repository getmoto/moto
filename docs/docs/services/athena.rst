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
- [X] create_data_catalog
- [X] create_named_query
- [ ] create_notebook
- [ ] create_prepared_statement
- [ ] create_presigned_notebook_url
- [X] create_work_group
- [ ] delete_data_catalog
- [ ] delete_named_query
- [ ] delete_notebook
- [ ] delete_prepared_statement
- [ ] delete_work_group
- [ ] export_notebook
- [ ] get_calculation_execution
- [ ] get_calculation_execution_code
- [ ] get_calculation_execution_status
- [X] get_data_catalog
- [ ] get_database
- [X] get_named_query
- [ ] get_notebook_metadata
- [ ] get_prepared_statement
- [X] get_query_execution
- [X] get_query_results
  
        Queries are not executed, so this call will always return 0 rows by default.

        When using decorators, you can use the internal API to manually set results:

        .. sourcecode:: python

            from moto.athena.models import athena_backends, QueryResults
            from moto.core import DEFAULT_ACCOUNT_ID

            backend = athena_backends[DEFAULT_ACCOUNT_ID]["us-east-1"]
            rows = [{'Data': [{'VarCharValue': '..'}]}]
            column_info = [{
                              'CatalogName': 'string',
                              'SchemaName': 'string',
                              'TableName': 'string',
                              'Name': 'string',
                              'Label': 'string',
                              'Type': 'string',
                              'Precision': 123,
                              'Scale': 123,
                              'Nullable': 'NOT_NULL',
                              'CaseSensitive': True
                          }]
            results = QueryResults(rows=rows, column_info=column_info)
            backend.query_results["test"] = results

            result = client.get_query_results(QueryExecutionId="test")
        
        When running in moto in server mode, you can set the result via moto-server
        REST API call:

        .. sourcecode:: python

            # Make query execution ID generation deterministic
            # by calling first /moto-api/seed:
            requests.get(
                "http://motoapi.amazonaws.com:5000/moto-api/seed?a=42",
            )

            exex_id = "bdd640fb-0667-4ad1-9c80-317fa3b1799d"
            athena_result = {
                "region": "eu-west-1",
                "query_execution_id": exex_id,
                "rows": [
                    {"Headers": ["first_column"]},
                    {"Data": [{"VarCharValue": "1"}]},
                ],
                "column_info": [
                    {
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
                    }
                ],
            }
            resp = requests.post(
                "http://motoapi.amazonaws.com:5000/moto-api/static/athena/region/query_executions",
                json=athena_result,
            )
            resp.status_code.should.equal(201)

            client = boto3.client("athena", region_name="eu-west-1")
            details = client.get_query_execution(QueryExecutionId=exex_id)["QueryExecution"]
            details.should.equal(athena_result)

- [ ] get_query_runtime_statistics
- [ ] get_session
- [ ] get_session_status
- [ ] get_table_metadata
- [X] get_work_group
- [ ] import_notebook
- [ ] list_application_dpu_sizes
- [ ] list_calculation_executions
- [X] list_data_catalogs
- [ ] list_databases
- [ ] list_engine_versions
- [ ] list_executors
- [ ] list_named_queries
- [ ] list_notebook_metadata
- [ ] list_notebook_sessions
- [ ] list_prepared_statements
- [X] list_query_executions
- [ ] list_sessions
- [ ] list_table_metadata
- [ ] list_tags_for_resource
- [X] list_work_groups
- [ ] start_calculation_execution
- [X] start_query_execution
- [ ] start_session
- [ ] stop_calculation_execution
- [X] stop_query_execution
- [ ] tag_resource
- [ ] terminate_session
- [ ] untag_resource
- [ ] update_data_catalog
- [ ] update_named_query
- [ ] update_notebook
- [ ] update_notebook_metadata
- [ ] update_prepared_statement
- [ ] update_work_group

