.. _implementedservice_cloudformation:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==============
cloudformation
==============

.. autoclass:: moto.cloudformation.models.CloudFormationBackend

|start-h3| Implemented features for this service |end-h3|

- [ ] activate_organizations_access
- [ ] activate_type
- [ ] batch_describe_type_configurations
- [ ] cancel_update_stack
- [ ] continue_update_rollback
- [X] create_change_set
- [ ] create_generated_template
- [X] create_stack
  
        The functionality behind EnableTerminationProtection is not yet implemented.
        

- [X] create_stack_instances
  
        The following parameters are not yet implemented: DeploymentTargets.AccountFilterType, DeploymentTargets.AccountsUrl, OperationPreferences, CallAs
        

- [X] create_stack_set
  
        The following parameters are not yet implemented: StackId, AdministrationRoleARN, AutoDeployment, ExecutionRoleName, CallAs, ClientRequestToken, ManagedExecution
        

- [ ] deactivate_organizations_access
- [ ] deactivate_type
- [X] delete_change_set
- [ ] delete_generated_template
- [X] delete_stack
- [X] delete_stack_instances
  
        The following parameters are not  yet implemented: DeploymentTargets, OperationPreferences, RetainStacks, OperationId, CallAs
        

- [X] delete_stack_set
- [ ] deregister_type
- [ ] describe_account_limits
- [X] describe_change_set
- [ ] describe_change_set_hooks
- [ ] describe_generated_template
- [ ] describe_organizations_access
- [ ] describe_publisher
- [ ] describe_resource_scan
- [ ] describe_stack_drift_detection_status
- [X] describe_stack_events
- [X] describe_stack_instance
- [X] describe_stack_resource
- [ ] describe_stack_resource_drifts
- [X] describe_stack_resources
- [X] describe_stack_set
- [X] describe_stack_set_operation
- [X] describe_stacks
- [ ] describe_type
- [ ] describe_type_registration
- [ ] detect_stack_drift
- [ ] detect_stack_resource_drift
- [ ] detect_stack_set_drift
- [ ] estimate_template_cost
- [X] execute_change_set
- [ ] get_generated_template
- [X] get_stack_policy
- [X] get_template
- [ ] get_template_summary
- [ ] import_stacks_to_stack_set
- [X] list_change_sets
- [X] list_exports
- [ ] list_generated_templates
- [ ] list_imports
- [ ] list_resource_scan_related_resources
- [ ] list_resource_scan_resources
- [ ] list_resource_scans
- [ ] list_stack_instance_resource_drifts
- [X] list_stack_instances
  
        Pagination is not yet implemented.
        The parameters StackInstanceAccount/StackInstanceRegion are not yet implemented.
        

- [X] list_stack_resources
- [ ] list_stack_set_auto_deployment_targets
- [X] list_stack_set_operation_results
- [X] list_stack_set_operations
- [X] list_stack_sets
- [X] list_stacks
- [ ] list_type_registrations
- [ ] list_type_versions
- [ ] list_types
- [ ] publish_type
- [ ] record_handler_progress
- [ ] register_publisher
- [ ] register_type
- [ ] rollback_stack
- [X] set_stack_policy
  
        Note that Moto does no validation/parsing/enforcement of this policy - we simply persist it.
        

- [ ] set_type_configuration
- [ ] set_type_default_version
- [ ] signal_resource
- [ ] start_resource_scan
- [X] stop_stack_set_operation
- [ ] test_type
- [ ] update_generated_template
- [X] update_stack
- [X] update_stack_instances
  
        Calling this will update the parameters, but the actual resources are not updated
        

- [X] update_stack_set
- [ ] update_termination_protection
- [X] validate_template

