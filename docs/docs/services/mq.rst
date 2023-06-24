.. _implementedservice_mq:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==
mq
==

.. autoclass:: moto.mq.models.MQBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_mq
            def test_mq_behaviour:
                boto3.client("mq")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_broker
- [X] create_configuration
- [X] create_tags
- [X] create_user
- [X] delete_broker
- [X] delete_tags
- [X] delete_user
- [X] describe_broker
- [ ] describe_broker_engine_types
- [ ] describe_broker_instance_options
- [X] describe_configuration
- [X] describe_configuration_revision
- [X] describe_user
- [X] list_brokers
  
        Pagination is not yet implemented
        

- [ ] list_configuration_revisions
- [X] list_configurations
  
        Pagination has not yet been implemented.
        

- [X] list_tags
- [X] list_users
- [ ] promote
- [X] reboot_broker
- [X] update_broker
- [X] update_configuration
  
        No validation occurs on the provided XML. The authenticationStrategy may be changed depending on the provided configuration.
        

- [X] update_user

