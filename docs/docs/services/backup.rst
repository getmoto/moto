.. _implementedservice_backup:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

======
backup
======

.. autoclass:: moto.backup.models.BackupBackend

|start-h3| Implemented features for this service |end-h3|

- [ ] associate_backup_vault_mpa_approval_team
- [ ] cancel_legal_hold
- [X] create_backup_plan
- [ ] create_backup_selection
- [X] create_backup_vault
- [ ] create_framework
- [ ] create_legal_hold
- [ ] create_logically_air_gapped_backup_vault
- [ ] create_report_plan
- [ ] create_restore_access_backup_vault
- [ ] create_restore_testing_plan
- [ ] create_restore_testing_selection
- [X] delete_backup_plan
- [ ] delete_backup_selection
- [ ] delete_backup_vault
- [ ] delete_backup_vault_access_policy
- [ ] delete_backup_vault_lock_configuration
- [ ] delete_backup_vault_notifications
- [ ] delete_framework
- [ ] delete_recovery_point
- [ ] delete_report_plan
- [ ] delete_restore_testing_plan
- [ ] delete_restore_testing_selection
- [ ] describe_backup_job
- [ ] describe_backup_vault
- [ ] describe_copy_job
- [ ] describe_framework
- [ ] describe_global_settings
- [ ] describe_protected_resource
- [ ] describe_recovery_point
- [ ] describe_region_settings
- [ ] describe_report_job
- [ ] describe_report_plan
- [ ] describe_restore_job
- [ ] disassociate_backup_vault_mpa_approval_team
- [ ] disassociate_recovery_point
- [ ] disassociate_recovery_point_from_parent
- [ ] export_backup_plan_template
- [X] get_backup_plan
- [ ] get_backup_plan_from_json
- [ ] get_backup_plan_from_template
- [ ] get_backup_selection
- [ ] get_backup_vault_access_policy
- [ ] get_backup_vault_notifications
- [ ] get_legal_hold
- [ ] get_recovery_point_index_details
- [ ] get_recovery_point_restore_metadata
- [ ] get_restore_job_metadata
- [ ] get_restore_testing_inferred_metadata
- [ ] get_restore_testing_plan
- [ ] get_restore_testing_selection
- [ ] get_supported_resource_types
- [ ] list_backup_job_summaries
- [ ] list_backup_jobs
- [ ] list_backup_plan_templates
- [ ] list_backup_plan_versions
- [X] list_backup_plans
  
        Pagination is not yet implemented
        

- [ ] list_backup_selections
- [X] list_backup_vaults
  
        Pagination is not yet implemented
        

- [ ] list_copy_job_summaries
- [ ] list_copy_jobs
- [ ] list_frameworks
- [ ] list_indexed_recovery_points
- [ ] list_legal_holds
- [ ] list_protected_resources
- [ ] list_protected_resources_by_backup_vault
- [ ] list_recovery_points_by_backup_vault
- [ ] list_recovery_points_by_legal_hold
- [ ] list_recovery_points_by_resource
- [ ] list_report_jobs
- [ ] list_report_plans
- [ ] list_restore_access_backup_vaults
- [ ] list_restore_job_summaries
- [ ] list_restore_jobs
- [ ] list_restore_jobs_by_protected_resource
- [ ] list_restore_testing_plans
- [ ] list_restore_testing_selections
- [X] list_tags
  
        Pagination is not yet implemented
        

- [ ] put_backup_vault_access_policy
- [ ] put_backup_vault_lock_configuration
- [ ] put_backup_vault_notifications
- [ ] put_restore_validation_result
- [ ] revoke_restore_access_backup_vault
- [ ] start_backup_job
- [ ] start_copy_job
- [ ] start_report_job
- [ ] start_restore_job
- [ ] stop_backup_job
- [X] tag_resource
- [X] untag_resource
- [ ] update_backup_plan
- [ ] update_framework
- [ ] update_global_settings
- [ ] update_recovery_point_index_settings
- [ ] update_recovery_point_lifecycle
- [ ] update_region_settings
- [ ] update_report_plan
- [ ] update_restore_testing_plan
- [ ] update_restore_testing_selection

