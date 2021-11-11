.. _implementedservice_elasticbeanstalk:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

================
elasticbeanstalk
================



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_elasticbeanstalk
            def test_elasticbeanstalk_behaviour:
                boto3.client("elasticbeanstalk")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] abort_environment_update
- [ ] apply_environment_managed_action
- [ ] associate_environment_operations_role
- [ ] check_dns_availability
- [ ] compose_environments
- [X] create_application
- [ ] create_application_version
- [ ] create_configuration_template
- [X] create_environment
- [ ] create_platform_version
- [ ] create_storage_location
- [ ] delete_application
- [ ] delete_application_version
- [ ] delete_configuration_template
- [ ] delete_environment_configuration
- [ ] delete_platform_version
- [ ] describe_account_attributes
- [ ] describe_application_versions
- [ ] describe_applications
- [ ] describe_configuration_options
- [ ] describe_configuration_settings
- [ ] describe_environment_health
- [ ] describe_environment_managed_action_history
- [ ] describe_environment_managed_actions
- [ ] describe_environment_resources
- [X] describe_environments
- [ ] describe_events
- [ ] describe_instances_health
- [ ] describe_platform_version
- [ ] disassociate_environment_operations_role
- [X] list_available_solution_stacks
- [ ] list_platform_branches
- [ ] list_platform_versions
- [X] list_tags_for_resource
- [ ] rebuild_environment
- [ ] request_environment_info
- [ ] restart_app_server
- [ ] retrieve_environment_info
- [ ] swap_environment_cnames
- [ ] terminate_environment
- [ ] update_application
- [ ] update_application_resource_lifecycle
- [ ] update_application_version
- [ ] update_configuration_template
- [ ] update_environment
- [X] update_tags_for_resource
- [ ] validate_configuration_settings

