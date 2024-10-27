.. _implementedservice_timestream-query:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

================
timestream-query
================

.. autoclass:: moto.timestreamquery.models.TimestreamQueryBackend

|start-h3| Implemented features for this service |end-h3|

- [ ] cancel_query
- [X] create_scheduled_query
- [X] delete_scheduled_query
- [ ] describe_account_settings
- [X] describe_endpoints
- [X] describe_scheduled_query
- [ ] execute_scheduled_query
- [ ] list_scheduled_queries
- [ ] list_tags_for_resource
- [ ] prepare_query
- [X] query
  
        Moto does not have a builtin time-series Database, so calling this endpoint will return zero results by default.

        You can use a dedicated API to configuring a queue of expected results.

        An example invocation looks like this:

        .. sourcecode:: python

            first_result = {
                'QueryId': 'some_id',
                'Rows': [...],
                'ColumnInfo': [...],
                'QueryStatus': ...
            }
            result_for_unknown_query_string = {
                'QueryId': 'unknown',
                'Rows': [...],
                'ColumnInfo': [...],
                'QueryStatus': ...
            }
            expected_results = {
                "account_id": "123456789012",  # This is the default - can be omitted
                "region": "us-east-1",  # This is the default - can be omitted
                "results": {
                    # Use the exact querystring, and a list of results for it
                    # For example
                    "SELECT data FROM mytable": [first_result, ...],
                    # Use None if the exact querystring is unknown/irrelevant
                    None: [result_for_unknown_query_string, ...],
                }
            }
            requests.post(
                "http://motoapi.amazonaws.com/moto-api/static/timestream/query-results",
                json=expected_results,
            )

        When calling `query(QueryString='SELECT data FROM mytable')`, the `first_result` will be returned.
        Call the query again for the second result, and so on.

        If you don't know the exact query strings, use the `None`-key. In the above example, when calling `SELECT something FROM unknown`, there are no results for that specific query, so `result_for_unknown_query_string` will be returned.

        Results for unknown queries are cached, so calling `SELECT something FROM unknown` will return the same result.

        

- [ ] tag_resource
- [ ] untag_resource
- [ ] update_account_settings
- [X] update_scheduled_query

