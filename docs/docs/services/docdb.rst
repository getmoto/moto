.. _implementedservice_docdb:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=====
docdb
=====

|start-h3| Implemented features for this service |end-h3|

- [ ] add_source_identifier_to_subscription
- [X] add_tags_to_resource
- [ ] apply_pending_maintenance_action
- [X] copy_db_cluster_parameter_group
- [X] copy_db_cluster_snapshot
- [X] create_db_cluster
- [X] create_db_cluster_parameter_group
- [X] create_db_cluster_snapshot
- [X] create_db_instance
- [X] create_db_subnet_group
- [X] create_event_subscription
- [X] create_global_cluster
- [X] delete_db_cluster
- [X] delete_db_cluster_parameter_group
- [X] delete_db_cluster_snapshot
- [X] delete_db_instance
- [X] delete_db_subnet_group
- [X] delete_event_subscription
- [X] delete_global_cluster
- [ ] describe_certificates
- [X] describe_db_cluster_parameter_groups
- [X] describe_db_cluster_parameters
- [X] describe_db_cluster_snapshot_attributes
- [X] describe_db_cluster_snapshots
- [X] describe_db_clusters
- [X] describe_db_engine_versions
  
Only a small, static set of engine versions is returned. These are the
default versions for the engines that Moto supports, plus the
DocumentDB versions (3.6.0, 4.0.0, 5.0.0).


- [X] describe_db_instances
- [X] describe_db_subnet_groups
- [X] describe_engine_default_cluster_parameters
  
Default parameters are only returned for the DocumentDB families.
Other families return an empty parameter list.


- [ ] describe_event_categories
- [X] describe_event_subscriptions
- [X] describe_events
- [X] describe_global_clusters
- [X] describe_orderable_db_instance_options
  
Only the Aurora-Postgresql and Neptune-engine is currently implemented


- [ ] describe_pending_maintenance_actions
- [X] failover_db_cluster
- [ ] failover_global_cluster
- [X] list_tags_for_resource
- [X] modify_db_cluster
- [X] modify_db_cluster_parameter_group
- [X] modify_db_cluster_snapshot_attribute
- [X] modify_db_instance
- [X] modify_db_subnet_group
- [ ] modify_event_subscription
- [ ] modify_global_cluster
- [X] reboot_db_instance
- [X] remove_from_global_cluster
- [ ] remove_source_identifier_from_subscription
- [X] remove_tags_from_resource
- [X] reset_db_cluster_parameter_group
- [X] restore_db_cluster_from_snapshot
- [X] restore_db_cluster_to_point_in_time
- [X] start_db_cluster
- [X] stop_db_cluster
- [ ] switchover_global_cluster

