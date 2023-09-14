.. _implementedservice_dms:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
dms
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_dms
            def test_dms_behaviour:
                boto3.client("dms")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_tags_to_resource
- [ ] apply_pending_maintenance_action
- [ ] batch_start_recommendations
- [ ] cancel_replication_task_assessment_run
- [ ] create_data_provider
- [ ] create_endpoint
- [ ] create_event_subscription
- [ ] create_fleet_advisor_collector
- [ ] create_instance_profile
- [ ] create_migration_project
- [ ] create_replication_config
- [ ] create_replication_instance
- [ ] create_replication_subnet_group
- [X] create_replication_task
  
        The following parameters are not yet implemented:
        CDCStartTime, CDCStartPosition, CDCStopPosition, Tags, TaskData, ResourceIdentifier
        

- [ ] delete_certificate
- [ ] delete_connection
- [ ] delete_data_provider
- [ ] delete_endpoint
- [ ] delete_event_subscription
- [ ] delete_fleet_advisor_collector
- [ ] delete_fleet_advisor_databases
- [ ] delete_instance_profile
- [ ] delete_migration_project
- [ ] delete_replication_config
- [ ] delete_replication_instance
- [ ] delete_replication_subnet_group
- [X] delete_replication_task
- [ ] delete_replication_task_assessment_run
- [ ] describe_account_attributes
- [ ] describe_applicable_individual_assessments
- [ ] describe_certificates
- [ ] describe_connections
- [ ] describe_conversion_configuration
- [ ] describe_data_providers
- [ ] describe_endpoint_settings
- [ ] describe_endpoint_types
- [ ] describe_endpoints
- [ ] describe_engine_versions
- [ ] describe_event_categories
- [ ] describe_event_subscriptions
- [ ] describe_events
- [ ] describe_extension_pack_associations
- [ ] describe_fleet_advisor_collectors
- [ ] describe_fleet_advisor_databases
- [ ] describe_fleet_advisor_lsa_analysis
- [ ] describe_fleet_advisor_schema_object_summary
- [ ] describe_fleet_advisor_schemas
- [ ] describe_instance_profiles
- [ ] describe_metadata_model_assessments
- [ ] describe_metadata_model_conversions
- [ ] describe_metadata_model_exports_as_script
- [ ] describe_metadata_model_exports_to_target
- [ ] describe_metadata_model_imports
- [ ] describe_migration_projects
- [ ] describe_orderable_replication_instances
- [ ] describe_pending_maintenance_actions
- [ ] describe_recommendation_limitations
- [ ] describe_recommendations
- [ ] describe_refresh_schemas_status
- [ ] describe_replication_configs
- [ ] describe_replication_instance_task_logs
- [ ] describe_replication_instances
- [ ] describe_replication_subnet_groups
- [ ] describe_replication_table_statistics
- [ ] describe_replication_task_assessment_results
- [ ] describe_replication_task_assessment_runs
- [ ] describe_replication_task_individual_assessments
- [X] describe_replication_tasks
  
        The parameter WithoutSettings has not yet been implemented
        

- [ ] describe_replications
- [ ] describe_schemas
- [ ] describe_table_statistics
- [ ] export_metadata_model_assessment
- [ ] import_certificate
- [ ] list_tags_for_resource
- [ ] modify_conversion_configuration
- [ ] modify_data_provider
- [ ] modify_endpoint
- [ ] modify_event_subscription
- [ ] modify_instance_profile
- [ ] modify_migration_project
- [ ] modify_replication_config
- [ ] modify_replication_instance
- [ ] modify_replication_subnet_group
- [ ] modify_replication_task
- [ ] move_replication_task
- [ ] reboot_replication_instance
- [ ] refresh_schemas
- [ ] reload_replication_tables
- [ ] reload_tables
- [ ] remove_tags_from_resource
- [ ] run_fleet_advisor_lsa_analysis
- [ ] start_extension_pack_association
- [ ] start_metadata_model_assessment
- [ ] start_metadata_model_conversion
- [ ] start_metadata_model_export_as_script
- [ ] start_metadata_model_export_to_target
- [ ] start_metadata_model_import
- [ ] start_recommendations
- [ ] start_replication
- [X] start_replication_task
  
        The following parameters have not yet been implemented:
        StartReplicationTaskType, CDCStartTime, CDCStartPosition, CDCStopPosition
        

- [ ] start_replication_task_assessment
- [ ] start_replication_task_assessment_run
- [ ] stop_replication
- [X] stop_replication_task
- [ ] test_connection
- [ ] update_subscriptions_to_event_bridge

