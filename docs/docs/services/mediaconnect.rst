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

- [ ] add_flow_media_streams
- [X] add_flow_outputs
- [ ] add_flow_sources
- [X] add_flow_vpc_interfaces
- [X] create_flow
- [X] delete_flow
- [X] describe_flow
- [ ] describe_offering
- [ ] describe_reservation
- [ ] grant_flow_entitlements
- [ ] list_entitlements
- [X] list_flows
- [ ] list_offerings
- [ ] list_reservations
- [X] list_tags_for_resource
- [ ] purchase_offering
- [ ] remove_flow_media_stream
- [X] remove_flow_output
- [ ] remove_flow_source
- [X] remove_flow_vpc_interface
- [ ] revoke_flow_entitlement
- [X] start_flow
- [X] stop_flow
- [X] tag_resource
- [ ] untag_resource
- [ ] update_flow
- [ ] update_flow_entitlement
- [ ] update_flow_media_stream
- [ ] update_flow_output
- [ ] update_flow_source

