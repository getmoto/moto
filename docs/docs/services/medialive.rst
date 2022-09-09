.. _implementedservice_medialive:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=========
medialive
=========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_medialive
            def test_medialive_behaviour:
                boto3.client("medialive")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] accept_input_device_transfer
- [ ] batch_delete
- [ ] batch_start
- [ ] batch_stop
- [ ] batch_update_schedule
- [ ] cancel_input_device_transfer
- [ ] claim_device
- [X] create_channel
  
        The RequestID and Reserved parameters are not yet implemented
        

- [X] create_input
  
        The VPC and RequestId parameters are not yet implemented
        

- [ ] create_input_security_group
- [ ] create_multiplex
- [ ] create_multiplex_program
- [ ] create_partner_input
- [ ] create_tags
- [X] delete_channel
- [X] delete_input
- [ ] delete_input_security_group
- [ ] delete_multiplex
- [ ] delete_multiplex_program
- [ ] delete_reservation
- [ ] delete_schedule
- [ ] delete_tags
- [X] describe_channel
- [X] describe_input
- [ ] describe_input_device
- [ ] describe_input_device_thumbnail
- [ ] describe_input_security_group
- [ ] describe_multiplex
- [ ] describe_multiplex_program
- [ ] describe_offering
- [ ] describe_reservation
- [ ] describe_schedule
- [X] list_channels
- [ ] list_input_device_transfers
- [ ] list_input_devices
- [ ] list_input_security_groups
- [X] list_inputs
- [ ] list_multiplex_programs
- [ ] list_multiplexes
- [ ] list_offerings
- [ ] list_reservations
- [ ] list_tags_for_resource
- [ ] purchase_offering
- [ ] reject_input_device_transfer
- [X] start_channel
- [ ] start_multiplex
- [X] stop_channel
- [ ] stop_multiplex
- [ ] transfer_input_device
- [X] update_channel
- [ ] update_channel_class
- [X] update_input
- [ ] update_input_device
- [ ] update_input_security_group
- [ ] update_multiplex
- [ ] update_multiplex_program
- [ ] update_reservation

