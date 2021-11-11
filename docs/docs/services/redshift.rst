.. _implementedservice_redshift:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
redshift
========



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_redshift
            def test_redshift_behaviour:
                boto3.client("redshift")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] accept_reserved_node_exchange
- [ ] add_partner
- [ ] associate_data_share_consumer
- [X] authorize_cluster_security_group_ingress
- [ ] authorize_data_share
- [ ] authorize_endpoint_access
- [ ] authorize_snapshot_access
- [ ] batch_delete_cluster_snapshots
- [ ] batch_modify_cluster_snapshots
- [ ] cancel_resize
- [ ] copy_cluster_snapshot
- [ ] create_authentication_profile
- [X] create_cluster
- [X] create_cluster_parameter_group
- [X] create_cluster_security_group
- [X] create_cluster_snapshot
- [X] create_cluster_subnet_group
- [ ] create_endpoint_access
- [ ] create_event_subscription
- [ ] create_hsm_client_certificate
- [ ] create_hsm_configuration
- [ ] create_scheduled_action
- [X] create_snapshot_copy_grant
- [ ] create_snapshot_schedule
- [X] create_tags
- [ ] create_usage_limit
- [ ] deauthorize_data_share
- [ ] delete_authentication_profile
- [X] delete_cluster
- [X] delete_cluster_parameter_group
- [X] delete_cluster_security_group
- [X] delete_cluster_snapshot
- [X] delete_cluster_subnet_group
- [ ] delete_endpoint_access
- [ ] delete_event_subscription
- [ ] delete_hsm_client_certificate
- [ ] delete_hsm_configuration
- [ ] delete_partner
- [ ] delete_scheduled_action
- [X] delete_snapshot_copy_grant
- [ ] delete_snapshot_schedule
- [X] delete_tags
- [ ] delete_usage_limit
- [ ] describe_account_attributes
- [ ] describe_authentication_profiles
- [ ] describe_cluster_db_revisions
- [X] describe_cluster_parameter_groups
- [ ] describe_cluster_parameters
- [X] describe_cluster_security_groups
- [X] describe_cluster_snapshots
- [X] describe_cluster_subnet_groups
- [ ] describe_cluster_tracks
- [ ] describe_cluster_versions
- [X] describe_clusters
- [ ] describe_data_shares
- [ ] describe_data_shares_for_consumer
- [ ] describe_data_shares_for_producer
- [ ] describe_default_cluster_parameters
- [ ] describe_endpoint_access
- [ ] describe_endpoint_authorization
- [ ] describe_event_categories
- [ ] describe_event_subscriptions
- [ ] describe_events
- [ ] describe_hsm_client_certificates
- [ ] describe_hsm_configurations
- [ ] describe_logging_status
- [ ] describe_node_configuration_options
- [ ] describe_orderable_cluster_options
- [ ] describe_partners
- [ ] describe_reserved_node_offerings
- [ ] describe_reserved_nodes
- [ ] describe_resize
- [ ] describe_scheduled_actions
- [X] describe_snapshot_copy_grants
- [ ] describe_snapshot_schedules
- [ ] describe_storage
- [ ] describe_table_restore_status
- [X] describe_tags
- [ ] describe_usage_limits
- [ ] disable_logging
- [X] disable_snapshot_copy
- [ ] disassociate_data_share_consumer
- [ ] enable_logging
- [X] enable_snapshot_copy
- [X] get_cluster_credentials
- [ ] get_reserved_node_exchange_offerings
- [ ] modify_aqua_configuration
- [ ] modify_authentication_profile
- [X] modify_cluster
- [ ] modify_cluster_db_revision
- [ ] modify_cluster_iam_roles
- [ ] modify_cluster_maintenance
- [ ] modify_cluster_parameter_group
- [ ] modify_cluster_snapshot
- [ ] modify_cluster_snapshot_schedule
- [ ] modify_cluster_subnet_group
- [ ] modify_endpoint_access
- [ ] modify_event_subscription
- [ ] modify_scheduled_action
- [X] modify_snapshot_copy_retention_period
- [ ] modify_snapshot_schedule
- [ ] modify_usage_limit
- [ ] pause_cluster
- [ ] purchase_reserved_node_offering
- [ ] reboot_cluster
- [ ] reject_data_share
- [ ] reset_cluster_parameter_group
- [ ] resize_cluster
- [X] restore_from_cluster_snapshot
- [ ] restore_table_from_cluster_snapshot
- [ ] resume_cluster
- [ ] revoke_cluster_security_group_ingress
- [ ] revoke_endpoint_access
- [ ] revoke_snapshot_access
- [ ] rotate_encryption_key
- [ ] update_partner_status

