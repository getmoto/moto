.. _implementedservice_events:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

======
events
======

.. autoclass:: moto.events.models.EventsBackend

|start-h3| Implemented features for this service |end-h3|

- [ ] activate_event_source
- [X] cancel_replay
- [X] create_api_destination
- [X] create_archive
- [X] create_connection
- [ ] create_endpoint
- [X] create_event_bus
- [X] create_partner_event_source
- [ ] deactivate_event_source
- [ ] deauthorize_connection
- [X] delete_api_destination
- [X] delete_archive
- [X] delete_connection
- [ ] delete_endpoint
- [X] delete_event_bus
- [X] delete_partner_event_source
- [X] delete_rule
- [X] describe_api_destination
- [X] describe_archive
- [X] describe_connection
- [ ] describe_endpoint
- [X] describe_event_bus
- [X] describe_event_source
- [X] describe_partner_event_source
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
  
        The following targets are supported at the moment:

         - CloudWatch Log Group
         - EventBridge Archive
         - SQS Queue + FIFO Queue
         - Cross-region/account EventBus
         - HTTP requests (only enabled when MOTO_EVENTS_INVOKE_HTTP=true)
        

- [X] put_partner_events
  
        Validation of the entries is not yet implemented.
        

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
- [X] update_archive
- [X] update_connection
- [ ] update_endpoint
- [ ] update_event_bus

