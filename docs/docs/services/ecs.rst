.. _implementedservice_ecs:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
ecs
===

.. autoclass:: moto.ecs.models.EC2ContainerServiceBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_ecs
            def test_ecs_behaviour:
                boto3.client("ecs")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_capacity_provider
- [X] create_cluster
- [X] create_service
- [X] create_task_set
- [X] delete_account_setting
- [X] delete_attributes
- [X] delete_capacity_provider
- [X] delete_cluster
- [X] delete_service
- [ ] delete_task_definitions
- [X] delete_task_set
  
        The Force-parameter is not yet implemented
        

- [X] deregister_container_instance
- [X] deregister_task_definition
- [X] describe_capacity_providers
- [X] describe_clusters
  
        Only include=TAGS is currently supported.
        

- [X] describe_container_instances
- [X] describe_services
- [X] describe_task_definition
- [X] describe_task_sets
- [X] describe_tasks
  
        Only include=TAGS is currently supported.
        

- [ ] discover_poll_endpoint
- [ ] execute_command
- [ ] get_task_protection
- [X] list_account_settings
- [X] list_attributes
  
        Pagination is not yet implemented
        

- [X] list_clusters
  
        maxSize and pagination not implemented
        

- [X] list_container_instances
- [X] list_services
- [ ] list_services_by_namespace
- [X] list_tags_for_resource
  Currently implemented only for task definitions and services

- [X] list_task_definition_families
  
        The Status and pagination parameters are not yet implemented
        

- [X] list_task_definitions
- [X] list_tasks
- [X] put_account_setting
- [ ] put_account_setting_default
- [X] put_attributes
- [X] put_cluster_capacity_providers
- [X] register_container_instance
- [X] register_task_definition
- [X] run_task
- [X] start_task
- [X] stop_task
- [ ] submit_attachment_state_changes
- [ ] submit_container_state_change
- [ ] submit_task_state_change
- [X] tag_resource
- [X] untag_resource
- [X] update_capacity_provider
- [X] update_cluster
  
        The serviceConnectDefaults-parameter is not yet implemented
        

- [ ] update_cluster_settings
- [ ] update_container_agent
- [X] update_container_instances_state
- [X] update_service
- [X] update_service_primary_task_set
  Updates task sets be PRIMARY or ACTIVE for given cluster:service task sets

- [ ] update_task_protection
- [X] update_task_set

