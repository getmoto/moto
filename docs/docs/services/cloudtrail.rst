.. _implementedservice_cloudtrail:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
cloudtrail
==========

.. autoclass:: moto.cloudtrail.models.CloudTrailBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_cloudtrail
            def test_cloudtrail_behaviour:
                boto3.client("cloudtrail")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_tags
- [ ] cancel_query
- [ ] create_event_data_store
- [X] create_trail
- [ ] delete_event_data_store
- [X] delete_trail
- [ ] describe_query
- [X] describe_trails
- [ ] get_event_data_store
- [ ] get_event_selectors
- [ ] get_insight_selectors
- [ ] get_query_results
- [X] get_trail
- [X] get_trail_status
- [ ] list_event_data_stores
- [ ] list_public_keys
- [ ] list_queries
- [ ] list_tags
- [X] list_trails
- [ ] lookup_events
- [ ] put_event_selectors
- [ ] put_insight_selectors
- [ ] remove_tags
- [ ] restore_event_data_store
- [X] start_logging
- [ ] start_query
- [X] stop_logging
- [ ] update_event_data_store
- [ ] update_trail

