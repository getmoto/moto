.. _implementedservice_rds:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
rds
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_rds
            def test_rds_behaviour:
                boto3.client("rds")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_role_to_db_cluster
- [ ] add_role_to_db_instance
- [ ] add_source_identifier_to_subscription
- [X] add_tags_to_resource
- [ ] apply_pending_maintenance_action
- [ ] authorize_db_security_group_ingress
- [ ] backtrack_db_cluster
- [X] cancel_export_task
- [ ] copy_db_cluster_parameter_group
- [ ] copy_db_cluster_snapshot
- [ ] copy_db_parameter_group
- [ ] copy_db_snapshot
- [ ] copy_option_group
- [ ] create_custom_db_engine_version
- [X] create_db_cluster
- [ ] create_db_cluster_endpoint
- [ ] create_db_cluster_parameter_group
- [X] create_db_cluster_snapshot
- [X] create_db_instance
- [ ] create_db_instance_read_replica
- [X] create_db_parameter_group
- [ ] create_db_proxy
- [ ] create_db_proxy_endpoint
- [X] create_db_security_group
- [X] create_db_snapshot
- [ ] create_db_subnet_group
- [X] create_event_subscription
- [ ] create_global_cluster
- [X] create_option_group
- [ ] delete_custom_db_engine_version
- [X] delete_db_cluster
- [ ] delete_db_cluster_endpoint
- [ ] delete_db_cluster_parameter_group
- [X] delete_db_cluster_snapshot
- [X] delete_db_instance
- [ ] delete_db_instance_automated_backup
- [X] delete_db_parameter_group
- [ ] delete_db_proxy
- [ ] delete_db_proxy_endpoint
- [ ] delete_db_security_group
- [X] delete_db_snapshot
- [ ] delete_db_subnet_group
- [X] delete_event_subscription
- [ ] delete_global_cluster
- [X] delete_option_group
- [ ] deregister_db_proxy_targets
- [ ] describe_account_attributes
- [ ] describe_certificates
- [ ] describe_db_cluster_backtracks
- [ ] describe_db_cluster_endpoints
- [ ] describe_db_cluster_parameter_groups
- [ ] describe_db_cluster_parameters
- [ ] describe_db_cluster_snapshot_attributes
- [X] describe_db_cluster_snapshots
- [X] describe_db_clusters
- [ ] describe_db_engine_versions
- [ ] describe_db_instance_automated_backups
- [X] describe_db_instances
- [ ] describe_db_log_files
- [X] describe_db_parameter_groups
- [ ] describe_db_parameters
- [ ] describe_db_proxies
- [ ] describe_db_proxy_endpoints
- [ ] describe_db_proxy_target_groups
- [ ] describe_db_proxy_targets
- [ ] describe_db_security_groups
- [ ] describe_db_snapshot_attributes
- [ ] describe_db_snapshots
- [ ] describe_db_subnet_groups
- [ ] describe_engine_default_cluster_parameters
- [ ] describe_engine_default_parameters
- [ ] describe_event_categories
- [X] describe_event_subscriptions
- [ ] describe_events
- [X] describe_export_tasks
- [ ] describe_global_clusters
- [X] describe_option_group_options
- [X] describe_option_groups
- [ ] describe_orderable_db_instance_options
- [ ] describe_pending_maintenance_actions
- [ ] describe_reserved_db_instances
- [ ] describe_reserved_db_instances_offerings
- [ ] describe_source_regions
- [ ] describe_valid_db_instance_modifications
- [ ] download_db_log_file_portion
- [ ] failover_db_cluster
- [ ] failover_global_cluster
- [X] list_tags_for_resource
- [ ] modify_certificates
- [ ] modify_current_db_cluster_capacity
- [ ] modify_custom_db_engine_version
- [ ] modify_db_cluster
- [ ] modify_db_cluster_endpoint
- [ ] modify_db_cluster_parameter_group
- [ ] modify_db_cluster_snapshot_attribute
- [X] modify_db_instance
- [X] modify_db_parameter_group
- [ ] modify_db_proxy
- [ ] modify_db_proxy_endpoint
- [ ] modify_db_proxy_target_group
- [ ] modify_db_snapshot
- [ ] modify_db_snapshot_attribute
- [X] modify_db_subnet_group
- [ ] modify_event_subscription
- [ ] modify_global_cluster
- [X] modify_option_group
- [ ] promote_read_replica
- [ ] promote_read_replica_db_cluster
- [ ] purchase_reserved_db_instances_offering
- [ ] reboot_db_cluster
- [X] reboot_db_instance
- [ ] register_db_proxy_targets
- [ ] remove_from_global_cluster
- [ ] remove_role_from_db_cluster
- [ ] remove_role_from_db_instance
- [ ] remove_source_identifier_from_subscription
- [X] remove_tags_from_resource
- [ ] reset_db_cluster_parameter_group
- [ ] reset_db_parameter_group
- [ ] restore_db_cluster_from_s3
- [X] restore_db_cluster_from_snapshot
- [ ] restore_db_cluster_to_point_in_time
- [X] restore_db_instance_from_db_snapshot
- [ ] restore_db_instance_from_s3
- [ ] restore_db_instance_to_point_in_time
- [ ] revoke_db_security_group_ingress
- [ ] start_activity_stream
- [X] start_db_cluster
- [X] start_db_instance
- [ ] start_db_instance_automated_backups_replication
- [X] start_export_task
- [ ] stop_activity_stream
- [X] stop_db_cluster
- [X] stop_db_instance
- [ ] stop_db_instance_automated_backups_replication

