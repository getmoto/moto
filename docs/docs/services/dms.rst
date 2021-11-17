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
- [ ] cancel_replication_task_assessment_run
- [ ] create_endpoint
- [ ] create_event_subscription
- [ ] create_replication_instance
- [ ] create_replication_subnet_group
- [X] create_replication_task
- [ ] delete_certificate
- [ ] delete_connection
- [ ] delete_endpoint
- [ ] delete_event_subscription
- [ ] delete_replication_instance
- [ ] delete_replication_subnet_group
- [X] delete_replication_task
- [ ] delete_replication_task_assessment_run
- [ ] describe_account_attributes
- [ ] describe_applicable_individual_assessments
- [ ] describe_certificates
- [ ] describe_connections
- [ ] describe_endpoint_settings
- [ ] describe_endpoint_types
- [ ] describe_endpoints
- [ ] describe_event_categories
- [ ] describe_event_subscriptions
- [ ] describe_events
- [ ] describe_orderable_replication_instances
- [ ] describe_pending_maintenance_actions
- [ ] describe_refresh_schemas_status
- [ ] describe_replication_instance_task_logs
- [ ] describe_replication_instances
- [ ] describe_replication_subnet_groups
- [ ] describe_replication_task_assessment_results
- [ ] describe_replication_task_assessment_runs
- [ ] describe_replication_task_individual_assessments
- [X] describe_replication_tasks
- [ ] describe_schemas
- [ ] describe_table_statistics
- [ ] import_certificate
- [ ] list_tags_for_resource
- [ ] modify_endpoint
- [ ] modify_event_subscription
- [ ] modify_replication_instance
- [ ] modify_replication_subnet_group
- [ ] modify_replication_task
- [ ] move_replication_task
- [ ] reboot_replication_instance
- [ ] refresh_schemas
- [ ] reload_tables
- [ ] remove_tags_from_resource
- [X] start_replication_task
- [ ] start_replication_task_assessment
- [ ] start_replication_task_assessment_run
- [X] stop_replication_task
- [ ] test_connection

