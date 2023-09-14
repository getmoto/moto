.. _implementedservice_rds-data:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
rds-data
========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_rdsdata
            def test_rdsdata_behaviour:
                boto3.client("rds-data")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] batch_execute_statement
- [ ] begin_transaction
- [ ] commit_transaction
- [ ] execute_sql
- [X] execute_statement
  
        There is no validation yet on any of the input parameters.

        SQL statements are not executed by Moto, so this call will always return 0 records by default.

        You can use a dedicated API to override this, by configuring a queue of expected results.

        A request to `execute_statement` will take the first result from that queue, and assign it to the provided SQL-query. Subsequent requests using the same SQL-query will return the same result. Other requests using a different SQL-query will take the next result from the queue, or return an empty result if the queue is empty.

        Configure this queue by making an HTTP request to `/moto-api/static/rds-data/statement-results`. An example invocation looks like this:

        .. sourcecode:: python

            expected_results = {
                "account_id": "123456789012",  # This is the default - can be omitted
                "region": "us-east-1",  # This is the default - can be omitted
                "results": [
                    {
                        "records": [...],
                        "columnMetadata": [...],
                        "numberOfRecordsUpdated": 42,
                        "generatedFields": [...],
                        "formattedRecords": "some json"
                    },
                    # other results as required
                ],
            }
            resp = requests.post(
                "http://motoapi.amazonaws.com:5000/moto-api/static/rds-data/statement-results",
                json=expected_results,
            )
            assert resp.status_code == 201

            rdsdata = boto3.client("rds-data", region_name="us-east-1")
            resp = rdsdata.execute_statement(resourceArn="not applicable", secretArn="not applicable", sql="SELECT some FROM thing")

        

- [ ] rollback_transaction

