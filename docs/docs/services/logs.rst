.. _implementedservice_logs:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

====
logs
====

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_logs
            def test_logs_behaviour:
                boto3.client("logs")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] associate_kms_key
- [ ] cancel_export_task
- [ ] create_delivery
- [X] create_export_task
- [ ] create_log_anomaly_detector
- [X] create_log_group
- [X] create_log_stream
- [ ] delete_account_policy
- [ ] delete_data_protection_policy
- [ ] delete_delivery
- [ ] delete_delivery_destination
- [ ] delete_delivery_destination_policy
- [ ] delete_delivery_source
- [X] delete_destination
- [ ] delete_log_anomaly_detector
- [X] delete_log_group
- [X] delete_log_stream
- [X] delete_metric_filter
- [ ] delete_query_definition
- [X] delete_resource_policy
  
        Remove resource policy with a policy name matching given name.
        

- [X] delete_retention_policy
- [X] delete_subscription_filter
- [ ] describe_account_policies
- [ ] describe_deliveries
- [ ] describe_delivery_destinations
- [ ] describe_delivery_sources
- [X] describe_destinations
- [X] describe_export_tasks
  
        Pagination is not yet implemented
        

- [X] describe_log_groups
- [X] describe_log_streams
- [X] describe_metric_filters
- [X] describe_queries
  
        Pagination is not yet implemented
        

- [ ] describe_query_definitions
- [X] describe_resource_policies
  
        Return list of resource policies.

        The next_token and limit arguments are ignored.  The maximum
        number of resource policies per region is a small number (less
        than 50), so pagination isn't needed.
        

- [X] describe_subscription_filters
- [ ] disassociate_kms_key
- [X] filter_log_events
  
        The following filter patterns are currently supported: Single Terms, Multiple Terms, Exact Phrases.
        If the pattern is not supported, all events are returned.
        

- [ ] get_data_protection_policy
- [ ] get_delivery
- [ ] get_delivery_destination
- [ ] get_delivery_destination_policy
- [ ] get_delivery_source
- [ ] get_log_anomaly_detector
- [X] get_log_events
- [ ] get_log_group_fields
- [ ] get_log_record
- [X] get_query_results
  
        Not all query commands are implemented yet. Please raise an issue if you encounter unexpected results.
        

- [ ] list_anomalies
- [ ] list_log_anomaly_detectors
- [X] list_tags_for_resource
- [X] list_tags_log_group
- [ ] put_account_policy
- [ ] put_data_protection_policy
- [ ] put_delivery_destination
- [ ] put_delivery_destination_policy
- [ ] put_delivery_source
- [X] put_destination
- [X] put_destination_policy
- [X] put_log_events
  
        The SequenceToken-parameter is not yet implemented
        

- [X] put_metric_filter
- [ ] put_query_definition
- [X] put_resource_policy
  
        Creates/updates resource policy and return policy object
        

- [X] put_retention_policy
- [X] put_subscription_filter
- [ ] start_live_tail
- [X] start_query
- [ ] stop_query
- [X] tag_log_group
- [X] tag_resource
- [ ] test_metric_filter
- [X] untag_log_group
- [X] untag_resource
- [ ] update_anomaly
- [ ] update_log_anomaly_detector

