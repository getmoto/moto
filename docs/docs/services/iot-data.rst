.. _implementedservice_iot-data:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
iot-data
========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_iotdata
            def test_iotdata_behaviour:
                boto3.client("iot-data")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] delete_thing_shadow
- [ ] get_retained_message
- [X] get_thing_shadow
- [ ] list_named_shadows_for_thing
- [ ] list_retained_messages
- [X] publish
- [X] update_thing_shadow
  
        spec of payload:
          - need node `state`
          - state node must be an Object
          - State contains an invalid node: 'foo'
        


