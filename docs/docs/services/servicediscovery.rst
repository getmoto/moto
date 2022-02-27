.. _implementedservice_servicediscovery:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

================
servicediscovery
================

.. autoclass:: moto.servicediscovery.models.ServiceDiscoveryBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_servicediscovery
            def test_servicediscovery_behaviour:
                boto3.client("servicediscovery")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_http_namespace
- [X] create_private_dns_namespace
- [X] create_public_dns_namespace
- [X] create_service
- [X] delete_namespace
- [X] delete_service
- [ ] deregister_instance
- [ ] discover_instances
- [ ] get_instance
- [ ] get_instances_health_status
- [X] get_namespace
- [X] get_operation
- [X] get_service
- [ ] list_instances
- [X] list_namespaces
  
        Pagination or the Filters-parameter is not yet implemented
        

- [X] list_operations
  
        Pagination or the Filters-argument is not yet implemented
        

- [X] list_services
  
        Pagination or the Filters-argument is not yet implemented
        

- [X] list_tags_for_resource
- [ ] register_instance
- [X] tag_resource
- [X] untag_resource
- [ ] update_http_namespace
- [ ] update_instance_custom_health_status
- [ ] update_private_dns_namespace
- [ ] update_public_dns_namespace
- [X] update_service

