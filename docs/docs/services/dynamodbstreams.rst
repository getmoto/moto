.. _implementedservice_dynamodbstreams:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===============
dynamodbstreams
===============



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_dynamodbstreams
            def test_dynamodbstreams_behaviour:
                boto3.client("dynamodbstreams")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] describe_stream
- [X] get_records
- [X] get_shard_iterator
- [X] list_streams

