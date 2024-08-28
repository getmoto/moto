.. _implementedservice_glue:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

====
glue
====

|start-h3| Implemented features for this service |end-h3|

- [X] batch_create_partition
- [ ] batch_delete_connection
- [X] batch_delete_partition
- [X] batch_delete_table
- [ ] batch_delete_table_version
- [ ] batch_get_blueprints
- [X] batch_get_crawlers
- [ ] batch_get_custom_entity_types
- [ ] batch_get_data_quality_result
- [ ] batch_get_dev_endpoints
- [X] batch_get_jobs
- [X] batch_get_partition
- [ ] batch_get_table_optimizer
- [X] batch_get_triggers
- [ ] batch_get_workflows
- [ ] batch_stop_job_run
- [X] batch_update_partition
- [ ] cancel_data_quality_rule_recommendation_run
- [ ] cancel_data_quality_ruleset_evaluation_run
- [ ] cancel_ml_task_run
- [ ] cancel_statement
- [ ] check_schema_version_validity
- [ ] create_blueprint
- [ ] create_classifier
- [ ] create_connection
- [X] create_crawler
- [ ] create_custom_entity_type
- [ ] create_data_quality_ruleset
- [X] create_database
- [ ] create_dev_endpoint
- [X] create_job
- [ ] create_ml_transform
- [X] create_partition
- [ ] create_partition_index
- [X] create_registry
- [X] create_schema
  
        The following parameters/features are not yet implemented: Glue Schema Registry: compatibility checks NONE | BACKWARD | BACKWARD_ALL | FORWARD | FORWARD_ALL | FULL | FULL_ALL and  Data format parsing and syntax validation.
        

- [ ] create_script
- [ ] create_security_configuration
- [X] create_session
- [X] create_table
- [ ] create_table_optimizer
- [X] create_trigger
- [ ] create_usage_profile
- [ ] create_user_defined_function
- [ ] create_workflow
- [ ] delete_blueprint
- [ ] delete_classifier
- [ ] delete_column_statistics_for_partition
- [ ] delete_column_statistics_for_table
- [ ] delete_connection
- [X] delete_crawler
- [ ] delete_custom_entity_type
- [ ] delete_data_quality_ruleset
- [X] delete_database
- [ ] delete_dev_endpoint
- [X] delete_job
- [ ] delete_ml_transform
- [X] delete_partition
- [ ] delete_partition_index
- [X] delete_registry
- [ ] delete_resource_policy
- [X] delete_schema
- [ ] delete_schema_versions
- [ ] delete_security_configuration
- [X] delete_session
- [X] delete_table
- [ ] delete_table_optimizer
- [X] delete_table_version
- [X] delete_trigger
- [ ] delete_usage_profile
- [ ] delete_user_defined_function
- [ ] delete_workflow
- [ ] get_blueprint
- [ ] get_blueprint_run
- [ ] get_blueprint_runs
- [ ] get_catalog_import_status
- [ ] get_classifier
- [ ] get_classifiers
- [ ] get_column_statistics_for_partition
- [ ] get_column_statistics_for_table
- [ ] get_column_statistics_task_run
- [ ] get_column_statistics_task_runs
- [ ] get_connection
- [ ] get_connections
- [X] get_crawler
- [ ] get_crawler_metrics
- [X] get_crawlers
- [ ] get_custom_entity_type
- [ ] get_data_catalog_encryption_settings
- [ ] get_data_quality_result
- [ ] get_data_quality_rule_recommendation_run
- [ ] get_data_quality_ruleset
- [ ] get_data_quality_ruleset_evaluation_run
- [X] get_database
- [X] get_databases
- [ ] get_dataflow_graph
- [ ] get_dev_endpoint
- [ ] get_dev_endpoints
- [X] get_job
- [ ] get_job_bookmark
- [X] get_job_run
- [ ] get_job_runs
- [X] get_jobs
- [ ] get_mapping
- [ ] get_ml_task_run
- [ ] get_ml_task_runs
- [ ] get_ml_transform
- [ ] get_ml_transforms
- [X] get_partition
- [ ] get_partition_indexes
- [X] get_partitions
  
        See https://docs.aws.amazon.com/glue/latest/webapi/API_GetPartitions.html
        for supported expressions.

        Expression caveats:

        - Column names must consist of UPPERCASE, lowercase, dots and underscores only.
        - Literal dates and timestamps must be valid, i.e. no support for February 31st.
        - LIKE expressions are converted to Python regexes, escaping special characters.
          Only % and _ wildcards are supported, and SQL escaping using [] does not work.
        

- [ ] get_plan
- [X] get_registry
- [ ] get_resource_policies
- [ ] get_resource_policy
- [X] get_schema
- [X] get_schema_by_definition
- [X] get_schema_version
- [ ] get_schema_versions_diff
- [ ] get_security_configuration
- [ ] get_security_configurations
- [X] get_session
- [ ] get_statement
- [X] get_table
- [ ] get_table_optimizer
- [X] get_table_version
- [X] get_table_versions
- [X] get_tables
- [X] get_tags
- [X] get_trigger
- [X] get_triggers
- [ ] get_unfiltered_partition_metadata
- [ ] get_unfiltered_partitions_metadata
- [ ] get_unfiltered_table_metadata
- [ ] get_usage_profile
- [ ] get_user_defined_function
- [ ] get_user_defined_functions
- [ ] get_workflow
- [ ] get_workflow_run
- [ ] get_workflow_run_properties
- [ ] get_workflow_runs
- [ ] import_catalog_to_glue
- [ ] list_blueprints
- [ ] list_column_statistics_task_runs
- [X] list_crawlers
- [ ] list_crawls
- [ ] list_custom_entity_types
- [ ] list_data_quality_results
- [ ] list_data_quality_rule_recommendation_runs
- [ ] list_data_quality_ruleset_evaluation_runs
- [ ] list_data_quality_rulesets
- [ ] list_dev_endpoints
- [X] list_jobs
- [ ] list_ml_transforms
- [X] list_registries
- [ ] list_schema_versions
- [ ] list_schemas
- [X] list_sessions
- [ ] list_statements
- [ ] list_table_optimizer_runs
- [X] list_triggers
- [ ] list_usage_profiles
- [ ] list_workflows
- [ ] put_data_catalog_encryption_settings
- [ ] put_resource_policy
- [X] put_schema_version_metadata
- [ ] put_workflow_run_properties
- [ ] query_schema_version_metadata
- [X] register_schema_version
- [ ] remove_schema_version_metadata
- [ ] reset_job_bookmark
- [ ] resume_workflow_run
- [ ] run_statement
- [ ] search_tables
- [ ] start_blueprint_run
- [ ] start_column_statistics_task_run
- [X] start_crawler
- [ ] start_crawler_schedule
- [ ] start_data_quality_rule_recommendation_run
- [ ] start_data_quality_ruleset_evaluation_run
- [ ] start_export_labels_task_run
- [ ] start_import_labels_task_run
- [X] start_job_run
- [ ] start_ml_evaluation_task_run
- [ ] start_ml_labeling_set_generation_task_run
- [X] start_trigger
- [ ] start_workflow_run
- [ ] stop_column_statistics_task_run
- [X] stop_crawler
- [ ] stop_crawler_schedule
- [X] stop_session
- [X] stop_trigger
- [ ] stop_workflow_run
- [X] tag_resource
- [X] untag_resource
- [ ] update_blueprint
- [ ] update_classifier
- [ ] update_column_statistics_for_partition
- [ ] update_column_statistics_for_table
- [ ] update_connection
- [ ] update_crawler
- [ ] update_crawler_schedule
- [ ] update_data_quality_ruleset
- [X] update_database
- [ ] update_dev_endpoint
- [ ] update_job
- [ ] update_job_from_source_control
- [ ] update_ml_transform
- [X] update_partition
- [ ] update_registry
- [X] update_schema
  
        The SchemaVersionNumber-argument is not yet implemented
        

- [ ] update_source_control_from_job
- [X] update_table
- [ ] update_table_optimizer
- [ ] update_trigger
- [ ] update_usage_profile
- [ ] update_user_defined_function
- [ ] update_workflow

