.. _implementedservice_greengrass:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
greengrass
==========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_greengrass
            def test_greengrass_behaviour:
                boto3.client("greengrass")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] associate_role_to_group
- [ ] associate_service_role_to_account
- [ ] create_connector_definition
- [ ] create_connector_definition_version
- [X] create_core_definition
- [X] create_core_definition_version
- [ ] create_deployment
- [ ] create_device_definition
- [ ] create_device_definition_version
- [ ] create_function_definition
- [ ] create_function_definition_version
- [ ] create_group
- [ ] create_group_certificate_authority
- [ ] create_group_version
- [ ] create_logger_definition
- [ ] create_logger_definition_version
- [ ] create_resource_definition
- [ ] create_resource_definition_version
- [ ] create_software_update_job
- [ ] create_subscription_definition
- [ ] create_subscription_definition_version
- [ ] delete_connector_definition
- [ ] delete_core_definition
- [ ] delete_device_definition
- [ ] delete_function_definition
- [ ] delete_group
- [ ] delete_logger_definition
- [ ] delete_resource_definition
- [ ] delete_subscription_definition
- [ ] disassociate_role_from_group
- [ ] disassociate_service_role_from_account
- [ ] get_associated_role
- [ ] get_bulk_deployment_status
- [ ] get_connectivity_info
- [ ] get_connector_definition
- [ ] get_connector_definition_version
- [ ] get_core_definition
- [ ] get_core_definition_version
- [ ] get_deployment_status
- [ ] get_device_definition
- [ ] get_device_definition_version
- [ ] get_function_definition
- [ ] get_function_definition_version
- [ ] get_group
- [ ] get_group_certificate_authority
- [ ] get_group_certificate_configuration
- [ ] get_group_version
- [ ] get_logger_definition
- [ ] get_logger_definition_version
- [ ] get_resource_definition
- [ ] get_resource_definition_version
- [ ] get_service_role_for_account
- [ ] get_subscription_definition
- [ ] get_subscription_definition_version
- [ ] get_thing_runtime_configuration
- [ ] list_bulk_deployment_detailed_reports
- [ ] list_bulk_deployments
- [ ] list_connector_definition_versions
- [ ] list_connector_definitions
- [ ] list_core_definition_versions
- [ ] list_core_definitions
- [ ] list_deployments
- [ ] list_device_definition_versions
- [ ] list_device_definitions
- [ ] list_function_definition_versions
- [ ] list_function_definitions
- [ ] list_group_certificate_authorities
- [ ] list_group_versions
- [ ] list_groups
- [ ] list_logger_definition_versions
- [ ] list_logger_definitions
- [ ] list_resource_definition_versions
- [ ] list_resource_definitions
- [ ] list_subscription_definition_versions
- [ ] list_subscription_definitions
- [ ] list_tags_for_resource
- [ ] reset_deployments
- [ ] start_bulk_deployment
- [ ] stop_bulk_deployment
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_connectivity_info
- [ ] update_connector_definition
- [ ] update_core_definition
- [ ] update_device_definition
- [ ] update_function_definition
- [ ] update_group
- [ ] update_group_certificate_configuration
- [ ] update_logger_definition
- [ ] update_resource_definition
- [ ] update_subscription_definition
- [ ] update_thing_runtime_configuration

