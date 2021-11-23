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
- [ ] create_export_task
- [X] create_log_group
- [X] create_log_stream
- [ ] delete_destination
- [X] delete_log_group
- [X] delete_log_stream
- [X] delete_metric_filter
- [ ] delete_query_definition
- [X] delete_resource_policy
  Remove resource policy with a policy name matching given name.

- [X] delete_retention_policy
- [X] delete_subscription_filter
- [ ] describe_destinations
- [ ] describe_export_tasks
- [X] describe_log_groups
- [X] describe_log_streams
- [X] describe_metric_filters
- [ ] describe_queries
- [ ] describe_query_definitions
- [X] describe_resource_policies
  Return list of resource policies.

        The next_token and limit arguments are ignored.  The maximum
        number of resource policies per region is a small number (less
        than 50), so pagination isn't needed.
        

- [X] describe_subscription_filters
- [ ] disassociate_kms_key
- [X] filter_log_events
- [X] get_log_events
- [ ] get_log_group_fields
- [ ] get_log_record
- [ ] get_query_results
- [X] list_tags_log_group
- [ ] put_destination
- [ ] put_destination_policy
- [X] put_log_events
- [X] put_metric_filter
- [ ] put_query_definition
- [X] put_resource_policy
  Creates/updates resource policy and return policy object

- [X] put_retention_policy
- [X] put_subscription_filter
- [X] start_query
- [ ] stop_query
- [X] tag_log_group
- [ ] test_metric_filter
- [X] untag_log_group

