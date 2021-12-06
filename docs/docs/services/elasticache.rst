.. _implementedservice_elasticache:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===========
elasticache
===========

.. autoclass:: moto.elasticache.models.ElastiCacheBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_elasticache
            def test_elasticache_behaviour:
                boto3.client("elasticache")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_tags_to_resource
- [ ] authorize_cache_security_group_ingress
- [ ] batch_apply_update_action
- [ ] batch_stop_update_action
- [ ] complete_migration
- [ ] copy_snapshot
- [ ] create_cache_cluster
- [ ] create_cache_parameter_group
- [ ] create_cache_security_group
- [ ] create_cache_subnet_group
- [ ] create_global_replication_group
- [ ] create_replication_group
- [ ] create_snapshot
- [X] create_user
- [ ] create_user_group
- [ ] decrease_node_groups_in_global_replication_group
- [ ] decrease_replica_count
- [ ] delete_cache_cluster
- [ ] delete_cache_parameter_group
- [ ] delete_cache_security_group
- [ ] delete_cache_subnet_group
- [ ] delete_global_replication_group
- [ ] delete_replication_group
- [ ] delete_snapshot
- [X] delete_user
- [ ] delete_user_group
- [ ] describe_cache_clusters
- [ ] describe_cache_engine_versions
- [ ] describe_cache_parameter_groups
- [ ] describe_cache_parameters
- [ ] describe_cache_security_groups
- [ ] describe_cache_subnet_groups
- [ ] describe_engine_default_parameters
- [ ] describe_events
- [ ] describe_global_replication_groups
- [ ] describe_replication_groups
- [ ] describe_reserved_cache_nodes
- [ ] describe_reserved_cache_nodes_offerings
- [ ] describe_service_updates
- [ ] describe_snapshots
- [ ] describe_update_actions
- [ ] describe_user_groups
- [X] describe_users
  
        Only the `user_id` parameter is currently supported.  
        Pagination is not yet implemented.
        

- [ ] disassociate_global_replication_group
- [ ] failover_global_replication_group
- [ ] increase_node_groups_in_global_replication_group
- [ ] increase_replica_count
- [ ] list_allowed_node_type_modifications
- [ ] list_tags_for_resource
- [ ] modify_cache_cluster
- [ ] modify_cache_parameter_group
- [ ] modify_cache_subnet_group
- [ ] modify_global_replication_group
- [ ] modify_replication_group
- [ ] modify_replication_group_shard_configuration
- [ ] modify_user
- [ ] modify_user_group
- [ ] purchase_reserved_cache_nodes_offering
- [ ] rebalance_slots_in_global_replication_group
- [ ] reboot_cache_cluster
- [ ] remove_tags_from_resource
- [ ] reset_cache_parameter_group
- [ ] revoke_cache_security_group_ingress
- [ ] start_migration
- [ ] test_failover

