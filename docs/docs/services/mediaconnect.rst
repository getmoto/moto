.. _implementedservice_mediaconnect:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

============
mediaconnect
============

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_mediaconnect
            def test_mediaconnect_behaviour:
                boto3.client("mediaconnect")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_bridge_outputs
- [ ] add_bridge_sources
- [ ] add_flow_media_streams
- [X] add_flow_outputs
- [X] add_flow_sources
- [X] add_flow_vpc_interfaces
- [ ] create_bridge
- [X] create_flow
- [ ] create_gateway
- [ ] delete_bridge
- [X] delete_flow
- [ ] delete_gateway
- [ ] deregister_gateway_instance
- [ ] describe_bridge
- [X] describe_flow
- [ ] describe_gateway
- [ ] describe_gateway_instance
- [ ] describe_offering
- [ ] describe_reservation
- [X] grant_flow_entitlements
- [ ] list_bridges
- [ ] list_entitlements
- [X] list_flows
  
        Pagination is not yet implemented
        

- [ ] list_gateway_instances
- [ ] list_gateways
- [ ] list_offerings
- [ ] list_reservations
- [X] list_tags_for_resource
- [ ] purchase_offering
- [ ] remove_bridge_output
- [ ] remove_bridge_source
- [ ] remove_flow_media_stream
- [X] remove_flow_output
- [ ] remove_flow_source
- [X] remove_flow_vpc_interface
- [X] revoke_flow_entitlement
- [X] start_flow
- [X] stop_flow
- [X] tag_resource
- [ ] untag_resource
- [ ] update_bridge
- [ ] update_bridge_output
- [ ] update_bridge_source
- [ ] update_bridge_state
- [ ] update_flow
- [X] update_flow_entitlement
- [ ] update_flow_media_stream
- [X] update_flow_output
- [X] update_flow_source
- [ ] update_gateway_instance

