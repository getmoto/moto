.. _implementedservice_mediapackage:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

============
mediapackage
============



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_mediapackage
            def test_mediapackage_behaviour:
                boto3.client("mediapackage")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] configure_logs
- [X] create_channel
- [ ] create_harvest_job
- [X] create_origin_endpoint
- [X] delete_channel
- [X] delete_origin_endpoint
- [X] describe_channel
- [ ] describe_harvest_job
- [X] describe_origin_endpoint
- [X] list_channels
- [ ] list_harvest_jobs
- [X] list_origin_endpoints
- [ ] list_tags_for_resource
- [ ] rotate_channel_credentials
- [ ] rotate_ingest_endpoint_credentials
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_channel
- [X] update_origin_endpoint

