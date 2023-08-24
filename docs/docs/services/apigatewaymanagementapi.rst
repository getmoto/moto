.. _implementedservice_apigatewaymanagementapi:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=======================
apigatewaymanagementapi
=======================

.. autoclass:: moto.apigatewaymanagementapi.models.ApiGatewayManagementApiBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_apigatewaymanagementapi
            def test_apigatewaymanagementapi_behaviour:
                boto3.client("apigatewaymanagementapi")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] delete_connection
- [X] get_connection
- [X] post_to_connection

