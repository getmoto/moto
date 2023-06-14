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

- [X] add_tags
- [ ] cancel_query
- [ ] create_channel
- [ ] create_event_data_store
- [X] create_trail
- [ ] delete_channel
- [ ] delete_event_data_store
- [ ] delete_resource_policy
- [X] delete_trail
- [ ] deregister_organization_delegated_admin
- [ ] describe_query
- [X] describe_trails
- [ ] get_channel
- [ ] get_event_data_store
- [X] get_event_selectors
- [ ] get_import
- [X] get_insight_selectors
- [ ] get_query_results
- [ ] get_resource_policy
- [X] get_trail
- [X] get_trail_status
- [ ] list_channels
- [ ] list_event_data_stores
- [ ] list_import_failures
- [ ] list_imports
- [ ] list_public_keys
- [ ] list_queries
- [X] list_tags
  
        Pagination is not yet implemented
        

- [X] list_trails
- [ ] lookup_events
- [X] put_event_selectors
- [X] put_insight_selectors
- [ ] put_resource_policy
- [ ] register_organization_delegated_admin
- [X] remove_tags
- [ ] restore_event_data_store
- [ ] start_event_data_store_ingestion
- [ ] start_import
- [X] start_logging
- [ ] start_query
- [ ] stop_event_data_store_ingestion
- [ ] stop_import
- [X] stop_logging
- [ ] update_channel
- [ ] update_event_data_store
- [X] update_trail

