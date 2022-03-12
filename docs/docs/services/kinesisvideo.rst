.. _implementedservice_kinesisvideo:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

============
kinesisvideo
============

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_kinesisvideo
            def test_kinesisvideo_behaviour:
                boto3.client("kinesisvideo")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] create_signaling_channel
- [X] create_stream
- [ ] delete_signaling_channel
- [X] delete_stream
  
        The CurrentVersion-parameter is not yet implemented
        

- [ ] describe_signaling_channel
- [X] describe_stream
- [X] get_data_endpoint
- [ ] get_signaling_channel_endpoint
- [ ] list_signaling_channels
- [X] list_streams
  
        Pagination and the StreamNameCondition-parameter are not yet implemented
        

- [ ] list_tags_for_resource
- [ ] list_tags_for_stream
- [ ] tag_resource
- [ ] tag_stream
- [ ] untag_resource
- [ ] untag_stream
- [ ] update_data_retention
- [ ] update_signaling_channel
- [ ] update_stream

