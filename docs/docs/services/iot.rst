.. _implementedservice_iot:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
iot
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_iot
            def test_iot_behaviour:
                boto3.client("iot")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] accept_certificate_transfer
- [ ] add_thing_to_billing_group
- [X] add_thing_to_thing_group
- [ ] associate_targets_with_job
- [X] attach_policy
- [X] attach_principal_policy
- [ ] attach_security_profile
- [X] attach_thing_principal
- [ ] cancel_audit_mitigation_actions_task
- [ ] cancel_audit_task
- [ ] cancel_certificate_transfer
- [ ] cancel_detect_mitigation_actions_task
- [X] cancel_job
- [X] cancel_job_execution
  
        The parameters ExpectedVersion and StatusDetails are not yet implemented
        

- [ ] clear_default_authorizer
- [ ] confirm_topic_rule_destination
- [ ] create_audit_suppression
- [ ] create_authorizer
- [ ] create_billing_group
- [X] create_certificate_from_csr
- [ ] create_custom_metric
- [ ] create_dimension
- [X] create_domain_configuration
  
        The ValidationCertificateArn-parameter is not yet implemented
        

- [ ] create_dynamic_thing_group
- [ ] create_fleet_metric
- [X] create_job
- [ ] create_job_template
- [X] create_keys_and_certificate
- [ ] create_mitigation_action
- [ ] create_ota_update
- [X] create_policy
- [X] create_policy_version
- [ ] create_provisioning_claim
- [ ] create_provisioning_template
- [ ] create_provisioning_template_version
- [ ] create_role_alias
- [ ] create_scheduled_audit
- [ ] create_security_profile
- [ ] create_stream
- [X] create_thing
- [X] create_thing_group
- [X] create_thing_type
- [X] create_topic_rule
- [ ] create_topic_rule_destination
- [ ] delete_account_audit_configuration
- [ ] delete_audit_suppression
- [ ] delete_authorizer
- [ ] delete_billing_group
- [X] delete_ca_certificate
- [X] delete_certificate
- [ ] delete_custom_metric
- [ ] delete_dimension
- [X] delete_domain_configuration
- [ ] delete_dynamic_thing_group
- [ ] delete_fleet_metric
- [X] delete_job
- [X] delete_job_execution
- [ ] delete_job_template
- [ ] delete_mitigation_action
- [ ] delete_ota_update
- [X] delete_policy
- [X] delete_policy_version
- [ ] delete_provisioning_template
- [ ] delete_provisioning_template_version
- [ ] delete_registration_code
- [ ] delete_role_alias
- [ ] delete_scheduled_audit
- [ ] delete_security_profile
- [ ] delete_stream
- [X] delete_thing
  
        The ExpectedVersion-parameter is not yet implemented
        

- [X] delete_thing_group
  
        The ExpectedVersion-parameter is not yet implemented
        

- [X] delete_thing_type
- [X] delete_topic_rule
- [ ] delete_topic_rule_destination
- [ ] delete_v2_logging_level
- [X] deprecate_thing_type
- [ ] describe_account_audit_configuration
- [ ] describe_audit_finding
- [ ] describe_audit_mitigation_actions_task
- [ ] describe_audit_suppression
- [ ] describe_audit_task
- [ ] describe_authorizer
- [ ] describe_billing_group
- [X] describe_ca_certificate
- [X] describe_certificate
- [ ] describe_custom_metric
- [ ] describe_default_authorizer
- [ ] describe_detect_mitigation_actions_task
- [ ] describe_dimension
- [X] describe_domain_configuration
- [X] describe_endpoint
- [ ] describe_event_configurations
- [ ] describe_fleet_metric
- [ ] describe_index
- [X] describe_job
- [X] describe_job_execution
- [ ] describe_job_template
- [ ] describe_managed_job_template
- [ ] describe_mitigation_action
- [ ] describe_provisioning_template
- [ ] describe_provisioning_template_version
- [ ] describe_role_alias
- [ ] describe_scheduled_audit
- [ ] describe_security_profile
- [ ] describe_stream
- [X] describe_thing
- [X] describe_thing_group
- [ ] describe_thing_registration_task
- [X] describe_thing_type
- [X] detach_policy
- [X] detach_principal_policy
- [ ] detach_security_profile
- [X] detach_thing_principal
- [X] disable_topic_rule
- [X] enable_topic_rule
- [ ] get_behavior_model_training_summaries
- [ ] get_buckets_aggregation
- [ ] get_cardinality
- [ ] get_effective_policies
- [ ] get_indexing_configuration
- [X] get_job_document
- [ ] get_logging_options
- [ ] get_ota_update
- [ ] get_percentiles
- [X] get_policy
- [X] get_policy_version
- [X] get_registration_code
- [ ] get_statistics
- [X] get_topic_rule
- [ ] get_topic_rule_destination
- [ ] get_v2_logging_options
- [ ] list_active_violations
- [X] list_attached_policies
- [ ] list_audit_findings
- [ ] list_audit_mitigation_actions_executions
- [ ] list_audit_mitigation_actions_tasks
- [ ] list_audit_suppressions
- [ ] list_audit_tasks
- [ ] list_authorizers
- [ ] list_billing_groups
- [ ] list_ca_certificates
- [X] list_certificates
  
        Pagination is not yet implemented
        

- [X] list_certificates_by_ca
  
        Pagination is not yet implemented
        

- [ ] list_custom_metrics
- [ ] list_detect_mitigation_actions_executions
- [ ] list_detect_mitigation_actions_tasks
- [ ] list_dimensions
- [X] list_domain_configurations
- [ ] list_fleet_metrics
- [ ] list_indices
- [X] list_job_executions_for_job
- [X] list_job_executions_for_thing
- [ ] list_job_templates
- [X] list_jobs
  
        The following parameter are not yet implemented: Status, TargetSelection, ThingGroupName, ThingGroupId
        

- [ ] list_managed_job_templates
- [ ] list_metric_values
- [ ] list_mitigation_actions
- [ ] list_ota_updates
- [ ] list_outgoing_certificates
- [X] list_policies
- [X] list_policy_principals
- [X] list_policy_versions
- [X] list_principal_policies
- [X] list_principal_things
- [ ] list_provisioning_template_versions
- [ ] list_provisioning_templates
- [ ] list_role_aliases
- [ ] list_scheduled_audits
- [ ] list_security_profiles
- [ ] list_security_profiles_for_target
- [ ] list_streams
- [ ] list_tags_for_resource
- [ ] list_targets_for_policy
- [ ] list_targets_for_security_profile
- [X] list_thing_groups
- [X] list_thing_groups_for_thing
  
        Pagination is not yet implemented
        

- [X] list_thing_principals
- [ ] list_thing_registration_task_reports
- [ ] list_thing_registration_tasks
- [X] list_thing_types
- [X] list_things
- [ ] list_things_in_billing_group
- [X] list_things_in_thing_group
  
        Pagination and the recursive-parameter is not yet implemented
        

- [ ] list_topic_rule_destinations
- [X] list_topic_rules
- [ ] list_v2_logging_levels
- [ ] list_violation_events
- [ ] put_verification_state_on_violation
- [X] register_ca_certificate
  
        The VerificationCertificate-parameter is not yet implemented
        

- [X] register_certificate
- [X] register_certificate_without_ca
- [ ] register_thing
- [ ] reject_certificate_transfer
- [ ] remove_thing_from_billing_group
- [X] remove_thing_from_thing_group
- [X] replace_topic_rule
- [X] search_index
  
        Pagination is not yet implemented. Only basic search queries are supported for now.
        

- [ ] set_default_authorizer
- [X] set_default_policy_version
- [ ] set_logging_options
- [ ] set_v2_logging_level
- [ ] set_v2_logging_options
- [ ] start_audit_mitigation_actions_task
- [ ] start_detect_mitigation_actions_task
- [ ] start_on_demand_audit_task
- [ ] start_thing_registration_task
- [ ] stop_thing_registration_task
- [ ] tag_resource
- [ ] test_authorization
- [ ] test_invoke_authorizer
- [ ] transfer_certificate
- [ ] untag_resource
- [ ] update_account_audit_configuration
- [ ] update_audit_suppression
- [ ] update_authorizer
- [ ] update_billing_group
- [X] update_ca_certificate
  
        The newAutoRegistrationStatus and removeAutoRegistration-parameters are not yet implemented
        

- [X] update_certificate
- [ ] update_custom_metric
- [ ] update_dimension
- [X] update_domain_configuration
- [ ] update_dynamic_thing_group
- [ ] update_event_configurations
- [ ] update_fleet_metric
- [ ] update_indexing_configuration
- [ ] update_job
- [ ] update_mitigation_action
- [ ] update_provisioning_template
- [ ] update_role_alias
- [ ] update_scheduled_audit
- [ ] update_security_profile
- [ ] update_stream
- [X] update_thing
  
        The ExpectedVersion-parameter is not yet implemented
        

- [X] update_thing_group
- [X] update_thing_groups_for_thing
- [ ] update_topic_rule_destination
- [ ] validate_security_profile_behaviors

