.. _implementedservice_sagemaker-runtime:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=================
sagemaker-runtime
=================

.. autoclass:: moto.sagemakerruntime.models.SageMakerRuntimeBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_sagemakerruntime
            def test_sagemakerruntime_behaviour:
                boto3.client("sagemaker-runtime")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] invoke_endpoint
  
        This call will return static data by default.

        You can use a dedicated API to override this, by configuring a queue of expected results.

        A request to `get_query_results` will take the first result from that queue. Subsequent requests using the same details will return the same result. Other requests using a different QueryExecutionId will take the next result from the queue, or return static data if the queue is empty.

        Configuring this queue by making an HTTP request to `/moto-api/static/sagemaker/endpoint-results`. An example invocation looks like this:

        .. sourcecode:: python

            expected_results = {
                "account_id": "123456789012",  # This is the default - can be omitted
                "region": "us-east-1",  # This is the default - can be omitted
                "results": [
                    {
                         "Body": "first body",
                         "ContentType": "text/xml",
                         "InvokedProductionVariant": "prod",
                         "CustomAttributes": "my_attr",
                     },
                    # other results as required
                ],
            }
            requests.post(
                "http://motoapi.amazonaws.com:5000/moto-api/static/sagemaker/endpoint-results",
                json=expected_results,
            )

            client = boto3.client("sagemaker", region_name="us-east-1")
            details = client.invoke_endpoint(EndpointName="asdf", Body="qwer")

        

- [ ] invoke_endpoint_async
- [ ] invoke_endpoint_with_response_stream

