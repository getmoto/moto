.. _implementedservice_events:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

======
events
======

.. autoclass:: moto.events.models.EventsBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_events
            def test_events_behaviour:
                boto3.client("events")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] activate_event_source
- [X] cancel_replay
- [X] create_api_destination
  
        Creates an API destination, which is an HTTP invocation endpoint configured as a target for events.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_CreateApiDestination.html

        Returns:
            dict
        

- [X] create_archive
- [X] create_connection
- [ ] create_endpoint
- [X] create_event_bus
- [ ] create_partner_event_source
- [ ] deactivate_event_source
- [ ] deauthorize_connection
- [X] delete_api_destination
  
        Deletes the specified API destination.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DeleteApiDestination.html

        Args:
            name: The name of the destination to delete.

        Raises:
            ResourceNotFoundException: When the destination is not present.

        Returns:
            dict

        

- [X] delete_archive
- [X] delete_connection
  
        Deletes a connection.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DeleteConnection.html

        Args:
            name: The name of the connection to delete.

        Raises:
            ResourceNotFoundException: When the connection is not present.

        Returns:
            dict
        

- [ ] delete_endpoint
- [X] delete_event_bus
- [ ] delete_partner_event_source
- [X] delete_rule
- [X] describe_api_destination
  
        Retrieves details about an API destination.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DescribeApiDestination.html
        Args:
            name: The name of the API destination to retrieve.

        Returns:
            dict
        

- [X] describe_archive
- [X] describe_connection
  
        Retrieves details about a connection.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DescribeConnection.html

        Args:
            name: The name of the connection to retrieve.

        Raises:
            ResourceNotFoundException: When the connection is not present.

        Returns:
            dict
        

- [ ] describe_endpoint
- [X] describe_event_bus
- [ ] describe_event_source
- [ ] describe_partner_event_source
- [X] describe_replay
- [X] describe_rule
- [X] disable_rule
- [X] enable_rule
- [X] list_api_destinations
- [X] list_archives
- [X] list_connections
- [ ] list_endpoints
- [X] list_event_buses
- [ ] list_event_sources
- [ ] list_partner_event_source_accounts
- [ ] list_partner_event_sources
- [X] list_replays
- [X] list_rule_names_by_target
- [X] list_rules
- [X] list_tags_for_resource
- [X] list_targets_by_rule
- [X] put_events
- [ ] put_partner_events
- [X] put_permission
- [X] put_rule
- [X] put_targets
- [X] remove_permission
- [X] remove_targets
- [X] start_replay
- [X] tag_resource
- [X] test_event_pattern
- [X] untag_resource
- [X] update_api_destination
  
        Creates an API destination, which is an HTTP invocation endpoint configured as a target for events.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_UpdateApiDestination.html

        Returns:
            dict
        

- [X] update_archive
- [X] update_connection
- [ ] update_endpoint

