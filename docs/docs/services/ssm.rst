.. _implementedservice_ssm:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
ssm
===

.. autoclass:: moto.ssm.models.SimpleSystemManagerBackend

|start-h3| Implemented features for this service |end-h3|

- [X] add_tags_to_resource
- [ ] associate_ops_item_related_item
- [ ] cancel_command
- [ ] cancel_maintenance_window_execution
- [ ] create_activation
- [ ] create_association
- [ ] create_association_batch
- [X] create_document
- [X] create_maintenance_window
  
        Creates a maintenance window. No error handling or input validation has been implemented yet.
        

- [ ] create_ops_item
- [ ] create_ops_metadata
- [X] create_patch_baseline
  
        Registers a patch baseline. No error handling or input validation has been implemented yet.
        

- [ ] create_resource_data_sync
- [ ] delete_activation
- [ ] delete_association
- [X] delete_document
- [ ] delete_inventory
- [X] delete_maintenance_window
  
        Assumes the provided WindowId exists. No error handling has been implemented yet.
        

- [ ] delete_ops_item
- [ ] delete_ops_metadata
- [X] delete_parameter
- [X] delete_parameters
- [X] delete_patch_baseline
  
        Assumes the provided BaselineId exists. No error handling has been implemented yet.
        

- [ ] delete_resource_data_sync
- [ ] delete_resource_policy
- [ ] deregister_managed_instance
- [ ] deregister_patch_baseline_for_patch_group
- [X] deregister_target_from_maintenance_window
  
        Deregisters a target from a maintenance window. No error handling has been implemented yet.
        

- [X] deregister_task_from_maintenance_window
- [ ] describe_activations
- [ ] describe_association
- [ ] describe_association_execution_targets
- [ ] describe_association_executions
- [ ] describe_automation_executions
- [ ] describe_automation_step_executions
- [ ] describe_available_patches
- [X] describe_document
- [X] describe_document_permission
  
        Parameters max_results, permission_type, and next_token not yet implemented
        

- [ ] describe_effective_instance_associations
- [ ] describe_effective_patches_for_patch_baseline
- [ ] describe_instance_associations_status
- [ ] describe_instance_information
- [ ] describe_instance_patch_states
- [ ] describe_instance_patch_states_for_patch_group
- [ ] describe_instance_patches
- [ ] describe_instance_properties
- [ ] describe_inventory_deletions
- [ ] describe_maintenance_window_execution_task_invocations
- [ ] describe_maintenance_window_execution_tasks
- [ ] describe_maintenance_window_executions
- [ ] describe_maintenance_window_schedule
- [X] describe_maintenance_window_targets
  
        Describes all targets for a maintenance window. No error handling has been implemented yet.
        

- [X] describe_maintenance_window_tasks
- [X] describe_maintenance_windows
  
        Returns all windows. No pagination has been implemented yet. Only filtering for Name is supported.
        The NextExecutionTime-field is not returned.

        

- [ ] describe_maintenance_windows_for_target
- [ ] describe_ops_items
- [X] describe_parameters
- [X] describe_patch_baselines
  
        Returns all baselines. No pagination has been implemented yet.
        

- [ ] describe_patch_group_state
- [ ] describe_patch_groups
- [ ] describe_patch_properties
- [ ] describe_sessions
- [ ] disassociate_ops_item_related_item
- [ ] get_automation_execution
- [ ] get_calendar_state
- [X] get_command_invocation
- [ ] get_connection_status
- [ ] get_default_patch_baseline
- [ ] get_deployable_patch_snapshot_for_instance
- [X] get_document
- [ ] get_inventory
- [ ] get_inventory_schema
- [X] get_maintenance_window
  
        The window is assumed to exist - no error handling has been implemented yet.
        The NextExecutionTime-field is not returned.
        

- [ ] get_maintenance_window_execution
- [ ] get_maintenance_window_execution_task
- [ ] get_maintenance_window_execution_task_invocation
- [ ] get_maintenance_window_task
- [ ] get_ops_item
- [ ] get_ops_metadata
- [ ] get_ops_summary
- [X] get_parameter
- [X] get_parameter_history
- [X] get_parameters
- [X] get_parameters_by_path
  Implement the get-parameters-by-path-API in the backend.

- [ ] get_patch_baseline
- [ ] get_patch_baseline_for_patch_group
- [ ] get_resource_policies
- [ ] get_service_setting
- [X] label_parameter_version
- [ ] list_association_versions
- [ ] list_associations
- [ ] list_command_invocations
- [X] list_commands
  
        Pagination and the Filters-parameter is not yet implemented
        

- [ ] list_compliance_items
- [ ] list_compliance_summaries
- [ ] list_document_metadata_history
- [ ] list_document_versions
- [X] list_documents
- [ ] list_inventory_entries
- [ ] list_ops_item_events
- [ ] list_ops_item_related_items
- [ ] list_ops_metadata
- [ ] list_resource_compliance_summaries
- [ ] list_resource_data_sync
- [X] list_tags_for_resource
- [X] modify_document_permission
- [ ] put_compliance_items
- [ ] put_inventory
- [X] put_parameter
- [ ] put_resource_policy
- [ ] register_default_patch_baseline
- [ ] register_patch_baseline_for_patch_group
- [X] register_target_with_maintenance_window
  
        Registers a target with a maintenance window. No error handling has been implemented yet.
        

- [X] register_task_with_maintenance_window
- [X] remove_tags_from_resource
- [ ] reset_service_setting
- [ ] resume_session
- [ ] send_automation_signal
- [X] send_command
- [ ] start_associations_once
- [ ] start_automation_execution
- [ ] start_change_request_execution
- [ ] start_session
- [ ] stop_automation_execution
- [ ] terminate_session
- [ ] unlabel_parameter_version
- [ ] update_association
- [ ] update_association_status
- [X] update_document
- [X] update_document_default_version
- [ ] update_document_metadata
- [ ] update_maintenance_window
- [ ] update_maintenance_window_target
- [ ] update_maintenance_window_task
- [ ] update_managed_instance_role
- [ ] update_ops_item
- [ ] update_ops_metadata
- [ ] update_patch_baseline
- [ ] update_resource_data_sync
- [ ] update_service_setting

