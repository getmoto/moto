.. _implementedservice_cloudformation:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==============
cloudformation
==============

.. autoclass:: moto.cloudformation.models.CloudFormationBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_cloudformation
            def test_cloudformation_behaviour:
                boto3.client("cloudformation")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] activate_type
- [ ] batch_describe_type_configurations
- [ ] cancel_update_stack
- [ ] continue_update_rollback
- [X] create_change_set
- [X] create_stack
- [X] create_stack_instances
- [X] create_stack_set
- [ ] deactivate_type
- [X] delete_change_set
- [X] delete_stack
- [X] delete_stack_instances
- [X] delete_stack_set
- [ ] deregister_type
- [ ] describe_account_limits
- [X] describe_change_set
- [ ] describe_change_set_hooks
- [ ] describe_publisher
- [ ] describe_stack_drift_detection_status
- [ ] describe_stack_events
- [ ] describe_stack_instance
- [ ] describe_stack_resource
- [ ] describe_stack_resource_drifts
- [ ] describe_stack_resources
- [ ] describe_stack_set
- [ ] describe_stack_set_operation
- [X] describe_stacks
- [ ] describe_type
- [ ] describe_type_registration
- [ ] detect_stack_drift
- [ ] detect_stack_resource_drift
- [ ] detect_stack_set_drift
- [ ] estimate_template_cost
- [X] execute_change_set
- [X] get_stack_policy
- [ ] get_template
- [ ] get_template_summary
- [ ] import_stacks_to_stack_set
- [X] list_change_sets
- [X] list_exports
- [ ] list_imports
- [ ] list_stack_instances
- [X] list_stack_resources
- [ ] list_stack_set_operation_results
- [ ] list_stack_set_operations
- [ ] list_stack_sets
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
- [ ] stop_stack_set_operation
- [ ] test_type
- [X] update_stack
- [ ] update_stack_instances
- [X] update_stack_set
- [ ] update_termination_protection
- [X] validate_template

