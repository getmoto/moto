.. _implementedservice_mediastore-data:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===============
mediastore-data
===============

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_mediastoredata
            def test_mediastoredata_behaviour:
                boto3.client("mediastore-data")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] delete_object
- [ ] describe_object
- [X] get_object
  
        The Range-parameter is not yet supported.
        

- [X] list_items
  
        The Path- and MaxResults-parameters are not yet supported.
        

- [X] put_object
  
        The following parameters are not yet implemented: ContentType, CacheControl, UploadAvailability
        


