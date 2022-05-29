.. _implementedservice_ec2:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
ec2
===

.. autoclass:: moto.ec2.models.EC2Backend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_ec2
            def test_ec2_behaviour:
                boto3.client("ec2")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] accept_reserved_instances_exchange_quote
- [ ] accept_transit_gateway_multicast_domain_associations
- [X] accept_transit_gateway_peering_attachment
- [ ] accept_transit_gateway_vpc_attachment
- [ ] accept_vpc_endpoint_connections
- [X] accept_vpc_peering_connection
- [ ] advertise_byoip_cidr
- [X] allocate_address
- [ ] allocate_hosts
- [ ] allocate_ipam_pool_cidr
- [ ] apply_security_groups_to_client_vpn_target_network
- [X] assign_ipv6_addresses
- [X] assign_private_ip_addresses
- [X] associate_address
- [ ] associate_client_vpn_target_network
- [X] associate_dhcp_options
- [ ] associate_enclave_certificate_iam_role
- [X] associate_iam_instance_profile
- [ ] associate_instance_event_window
- [X] associate_route_table
- [X] associate_subnet_cidr_block
- [ ] associate_transit_gateway_multicast_domain
- [X] associate_transit_gateway_route_table
- [ ] associate_trunk_interface
- [X] associate_vpc_cidr_block
- [ ] attach_classic_link_vpc
- [X] attach_internet_gateway
- [X] attach_network_interface
- [X] attach_volume
- [X] attach_vpn_gateway
- [ ] authorize_client_vpn_ingress
- [X] authorize_security_group_egress
- [X] authorize_security_group_ingress
- [ ] bundle_instance
- [ ] cancel_bundle_task
- [ ] cancel_capacity_reservation
- [ ] cancel_capacity_reservation_fleets
- [ ] cancel_conversion_task
- [ ] cancel_export_task
- [ ] cancel_import_task
- [ ] cancel_reserved_instances_listing
- [X] cancel_spot_fleet_requests
- [X] cancel_spot_instance_requests
- [ ] confirm_product_instance
- [ ] copy_fpga_image
- [X] copy_image
- [X] copy_snapshot
- [ ] create_capacity_reservation
- [ ] create_capacity_reservation_fleet
- [X] create_carrier_gateway
- [ ] create_client_vpn_endpoint
- [ ] create_client_vpn_route
- [X] create_customer_gateway
- [ ] create_default_subnet
- [ ] create_default_vpc
- [X] create_dhcp_options
- [X] create_egress_only_internet_gateway
- [ ] create_fleet
- [X] create_flow_logs
- [ ] create_fpga_image
- [X] create_image
- [ ] create_instance_event_window
- [ ] create_instance_export_task
- [X] create_internet_gateway
- [ ] create_ipam
- [ ] create_ipam_pool
- [ ] create_ipam_scope
- [X] create_key_pair
- [X] create_launch_template
- [ ] create_launch_template_version
- [ ] create_local_gateway_route
- [ ] create_local_gateway_route_table_vpc_association
- [X] create_managed_prefix_list
- [X] create_nat_gateway
- [X] create_network_acl
- [X] create_network_acl_entry
- [ ] create_network_insights_access_scope
- [ ] create_network_insights_path
- [X] create_network_interface
- [ ] create_network_interface_permission
- [ ] create_placement_group
- [ ] create_public_ipv4_pool
- [ ] create_replace_root_volume_task
- [ ] create_reserved_instances_listing
- [ ] create_restore_image_task
- [X] create_route
- [X] create_route_table
- [X] create_security_group
- [X] create_snapshot
- [X] create_snapshots
  
        The CopyTagsFromSource-parameter is not yet implemented.
        

- [ ] create_spot_datafeed_subscription
- [ ] create_store_image_task
- [X] create_subnet
- [ ] create_subnet_cidr_reservation
- [X] create_tags
- [ ] create_traffic_mirror_filter
- [ ] create_traffic_mirror_filter_rule
- [ ] create_traffic_mirror_session
- [ ] create_traffic_mirror_target
- [X] create_transit_gateway
- [ ] create_transit_gateway_connect
- [ ] create_transit_gateway_connect_peer
- [ ] create_transit_gateway_multicast_domain
- [X] create_transit_gateway_peering_attachment
- [ ] create_transit_gateway_prefix_list_reference
- [X] create_transit_gateway_route
- [X] create_transit_gateway_route_table
- [X] create_transit_gateway_vpc_attachment
- [X] create_volume
- [X] create_vpc
- [X] create_vpc_endpoint
- [ ] create_vpc_endpoint_connection_notification
- [X] create_vpc_endpoint_service_configuration
- [X] create_vpc_peering_connection
- [X] create_vpn_connection
- [ ] create_vpn_connection_route
- [X] create_vpn_gateway
- [X] delete_carrier_gateway
- [ ] delete_client_vpn_endpoint
- [ ] delete_client_vpn_route
- [X] delete_customer_gateway
- [ ] delete_dhcp_options
- [X] delete_egress_only_internet_gateway
- [ ] delete_fleets
- [X] delete_flow_logs
- [ ] delete_fpga_image
- [ ] delete_instance_event_window
- [X] delete_internet_gateway
- [ ] delete_ipam
- [ ] delete_ipam_pool
- [ ] delete_ipam_scope
- [X] delete_key_pair
- [X] delete_launch_template
- [ ] delete_launch_template_versions
- [ ] delete_local_gateway_route
- [ ] delete_local_gateway_route_table_vpc_association
- [X] delete_managed_prefix_list
- [X] delete_nat_gateway
- [X] delete_network_acl
- [X] delete_network_acl_entry
- [ ] delete_network_insights_access_scope
- [ ] delete_network_insights_access_scope_analysis
- [ ] delete_network_insights_analysis
- [ ] delete_network_insights_path
- [X] delete_network_interface
- [ ] delete_network_interface_permission
- [ ] delete_placement_group
- [ ] delete_public_ipv4_pool
- [ ] delete_queued_reserved_instances
- [X] delete_route
- [X] delete_route_table
- [X] delete_security_group
- [X] delete_snapshot
- [ ] delete_spot_datafeed_subscription
- [X] delete_subnet
- [ ] delete_subnet_cidr_reservation
- [X] delete_tags
- [ ] delete_traffic_mirror_filter
- [ ] delete_traffic_mirror_filter_rule
- [ ] delete_traffic_mirror_session
- [ ] delete_traffic_mirror_target
- [X] delete_transit_gateway
- [ ] delete_transit_gateway_connect
- [ ] delete_transit_gateway_connect_peer
- [ ] delete_transit_gateway_multicast_domain
- [X] delete_transit_gateway_peering_attachment
- [ ] delete_transit_gateway_prefix_list_reference
- [X] delete_transit_gateway_route
- [X] delete_transit_gateway_route_table
- [X] delete_transit_gateway_vpc_attachment
- [X] delete_volume
- [X] delete_vpc
- [ ] delete_vpc_endpoint_connection_notifications
- [X] delete_vpc_endpoint_service_configurations
- [X] delete_vpc_endpoints
- [X] delete_vpc_peering_connection
- [X] delete_vpn_connection
- [ ] delete_vpn_connection_route
- [X] delete_vpn_gateway
- [ ] deprovision_byoip_cidr
- [ ] deprovision_ipam_pool_cidr
- [ ] deprovision_public_ipv4_pool_cidr
- [X] deregister_image
- [ ] deregister_instance_event_notification_attributes
- [ ] deregister_transit_gateway_multicast_group_members
- [ ] deregister_transit_gateway_multicast_group_sources
- [ ] describe_account_attributes
- [X] describe_addresses
- [ ] describe_addresses_attribute
- [ ] describe_aggregate_id_format
- [X] describe_availability_zones
- [ ] describe_bundle_tasks
- [ ] describe_byoip_cidrs
- [ ] describe_capacity_reservation_fleets
- [ ] describe_capacity_reservations
- [X] describe_carrier_gateways
- [ ] describe_classic_link_instances
- [ ] describe_client_vpn_authorization_rules
- [ ] describe_client_vpn_connections
- [ ] describe_client_vpn_endpoints
- [ ] describe_client_vpn_routes
- [ ] describe_client_vpn_target_networks
- [ ] describe_coip_pools
- [ ] describe_conversion_tasks
- [ ] describe_customer_gateways
- [X] describe_dhcp_options
- [X] describe_egress_only_internet_gateways
  
        The Filters-argument is not yet supported
        

- [ ] describe_elastic_gpus
- [ ] describe_export_image_tasks
- [ ] describe_export_tasks
- [ ] describe_fast_launch_images
- [ ] describe_fast_snapshot_restores
- [ ] describe_fleet_history
- [ ] describe_fleet_instances
- [ ] describe_fleets
- [X] describe_flow_logs
- [ ] describe_fpga_image_attribute
- [ ] describe_fpga_images
- [ ] describe_host_reservation_offerings
- [ ] describe_host_reservations
- [ ] describe_hosts
- [X] describe_iam_instance_profile_associations
- [ ] describe_id_format
- [ ] describe_identity_id_format
- [ ] describe_image_attribute
- [X] describe_images
- [ ] describe_import_image_tasks
- [ ] describe_import_snapshot_tasks
- [X] describe_instance_attribute
- [X] describe_instance_credit_specifications
- [ ] describe_instance_event_notification_attributes
- [ ] describe_instance_event_windows
- [X] describe_instance_status
- [X] describe_instance_type_offerings
- [X] describe_instance_types
- [X] describe_instances
- [X] describe_internet_gateways
- [ ] describe_ipam_pools
- [ ] describe_ipam_scopes
- [ ] describe_ipams
- [ ] describe_ipv6_pools
- [X] describe_key_pairs
- [ ] describe_launch_template_versions
- [X] describe_launch_templates
- [ ] describe_local_gateway_route_table_virtual_interface_group_associations
- [ ] describe_local_gateway_route_table_vpc_associations
- [ ] describe_local_gateway_route_tables
- [ ] describe_local_gateway_virtual_interface_groups
- [ ] describe_local_gateway_virtual_interfaces
- [ ] describe_local_gateways
- [X] describe_managed_prefix_lists
- [ ] describe_moving_addresses
- [X] describe_nat_gateways
- [X] describe_network_acls
- [ ] describe_network_insights_access_scope_analyses
- [ ] describe_network_insights_access_scopes
- [ ] describe_network_insights_analyses
- [ ] describe_network_insights_paths
- [ ] describe_network_interface_attribute
- [ ] describe_network_interface_permissions
- [X] describe_network_interfaces
- [ ] describe_placement_groups
- [ ] describe_prefix_lists
- [ ] describe_principal_id_format
- [ ] describe_public_ipv4_pools
- [X] describe_regions
- [ ] describe_replace_root_volume_tasks
- [ ] describe_reserved_instances
- [ ] describe_reserved_instances_listings
- [ ] describe_reserved_instances_modifications
- [ ] describe_reserved_instances_offerings
- [X] describe_route_tables
- [ ] describe_scheduled_instance_availability
- [ ] describe_scheduled_instances
- [ ] describe_security_group_references
- [ ] describe_security_group_rules
- [X] describe_security_groups
- [ ] describe_snapshot_attribute
- [ ] describe_snapshot_tier_status
- [X] describe_snapshots
- [ ] describe_spot_datafeed_subscription
- [X] describe_spot_fleet_instances
- [ ] describe_spot_fleet_request_history
- [X] describe_spot_fleet_requests
- [X] describe_spot_instance_requests
- [X] describe_spot_price_history
- [ ] describe_stale_security_groups
- [ ] describe_store_image_tasks
- [ ] describe_subnets
- [X] describe_tags
- [ ] describe_traffic_mirror_filters
- [ ] describe_traffic_mirror_sessions
- [ ] describe_traffic_mirror_targets
- [X] describe_transit_gateway_attachments
- [ ] describe_transit_gateway_connect_peers
- [ ] describe_transit_gateway_connects
- [ ] describe_transit_gateway_multicast_domains
- [X] describe_transit_gateway_peering_attachments
- [ ] describe_transit_gateway_route_tables
- [X] describe_transit_gateway_vpc_attachments
- [X] describe_transit_gateways
- [ ] describe_trunk_interface_associations
- [ ] describe_volume_attribute
- [ ] describe_volume_status
- [X] describe_volumes
- [ ] describe_volumes_modifications
- [X] describe_vpc_attribute
- [ ] describe_vpc_classic_link
- [ ] describe_vpc_classic_link_dns_support
- [ ] describe_vpc_endpoint_connection_notifications
- [ ] describe_vpc_endpoint_connections
- [X] describe_vpc_endpoint_service_configurations
  
        The Filters, MaxResults, NextToken parameters are not yet implemented
        

- [X] describe_vpc_endpoint_service_permissions
  
        The Filters, MaxResults, NextToken parameters are not yet implemented
        

- [X] describe_vpc_endpoint_services
  Return info on services to which you can create a VPC endpoint.

        Currently only the default endpoing services are returned.  When
        create_vpc_endpoint_service_configuration() is implemented, a
        list of those private endpoints would be kept and when this API
        is invoked, those private endpoints would be added to the list of
        default endpoint services.

        The DryRun parameter is ignored.
        

- [X] describe_vpc_endpoints
- [X] describe_vpc_peering_connections
- [X] describe_vpcs
- [X] describe_vpn_connections
- [X] describe_vpn_gateways
- [ ] detach_classic_link_vpc
- [X] detach_internet_gateway
- [X] detach_network_interface
- [X] detach_volume
- [X] detach_vpn_gateway
- [X] disable_ebs_encryption_by_default
- [ ] disable_fast_launch
- [ ] disable_fast_snapshot_restores
- [ ] disable_image_deprecation
- [ ] disable_ipam_organization_admin_account
- [ ] disable_serial_console_access
- [X] disable_transit_gateway_route_table_propagation
- [ ] disable_vgw_route_propagation
- [X] disable_vpc_classic_link
- [X] disable_vpc_classic_link_dns_support
- [X] disassociate_address
- [ ] disassociate_client_vpn_target_network
- [ ] disassociate_enclave_certificate_iam_role
- [X] disassociate_iam_instance_profile
- [ ] disassociate_instance_event_window
- [X] disassociate_route_table
- [X] disassociate_subnet_cidr_block
- [ ] disassociate_transit_gateway_multicast_domain
- [X] disassociate_transit_gateway_route_table
- [ ] disassociate_trunk_interface
- [X] disassociate_vpc_cidr_block
- [X] enable_ebs_encryption_by_default
- [ ] enable_fast_launch
- [ ] enable_fast_snapshot_restores
- [ ] enable_image_deprecation
- [ ] enable_ipam_organization_admin_account
- [ ] enable_serial_console_access
- [X] enable_transit_gateway_route_table_propagation
- [ ] enable_vgw_route_propagation
- [ ] enable_volume_io
- [X] enable_vpc_classic_link
- [X] enable_vpc_classic_link_dns_support
- [ ] export_client_vpn_client_certificate_revocation_list
- [ ] export_client_vpn_client_configuration
- [ ] export_image
- [ ] export_transit_gateway_routes
- [ ] get_associated_enclave_certificate_iam_roles
- [ ] get_associated_ipv6_pool_cidrs
- [ ] get_capacity_reservation_usage
- [ ] get_coip_pool_usage
- [ ] get_console_output
- [ ] get_console_screenshot
- [ ] get_default_credit_specification
- [ ] get_ebs_default_kms_key_id
- [X] get_ebs_encryption_by_default
- [ ] get_flow_logs_integration_template
- [ ] get_groups_for_capacity_reservation
- [ ] get_host_reservation_purchase_preview
- [ ] get_instance_types_from_instance_requirements
- [ ] get_instance_uefi_data
- [ ] get_ipam_address_history
- [ ] get_ipam_pool_allocations
- [ ] get_ipam_pool_cidrs
- [ ] get_ipam_resource_cidrs
- [ ] get_launch_template_data
- [ ] get_managed_prefix_list_associations
- [X] get_managed_prefix_list_entries
- [ ] get_network_insights_access_scope_analysis_findings
- [ ] get_network_insights_access_scope_content
- [ ] get_password_data
- [ ] get_reserved_instances_exchange_quote
- [ ] get_serial_console_access_status
- [ ] get_spot_placement_scores
- [ ] get_subnet_cidr_reservations
- [ ] get_transit_gateway_attachment_propagations
- [ ] get_transit_gateway_multicast_domain_associations
- [ ] get_transit_gateway_prefix_list_references
- [ ] get_transit_gateway_route_table_associations
- [ ] get_transit_gateway_route_table_propagations
- [ ] get_vpn_connection_device_sample_configuration
- [ ] get_vpn_connection_device_types
- [ ] import_client_vpn_client_certificate_revocation_list
- [ ] import_image
- [ ] import_instance
- [X] import_key_pair
- [ ] import_snapshot
- [ ] import_volume
- [ ] list_images_in_recycle_bin
- [ ] list_snapshots_in_recycle_bin
- [ ] modify_address_attribute
- [ ] modify_availability_zone_group
- [ ] modify_capacity_reservation
- [ ] modify_capacity_reservation_fleet
- [ ] modify_client_vpn_endpoint
- [ ] modify_default_credit_specification
- [ ] modify_ebs_default_kms_key_id
- [ ] modify_fleet
- [ ] modify_fpga_image_attribute
- [ ] modify_hosts
- [ ] modify_id_format
- [ ] modify_identity_id_format
- [ ] modify_image_attribute
- [X] modify_instance_attribute
- [ ] modify_instance_capacity_reservation_attributes
- [ ] modify_instance_credit_specification
- [ ] modify_instance_event_start_time
- [ ] modify_instance_event_window
- [ ] modify_instance_maintenance_options
- [ ] modify_instance_metadata_options
- [ ] modify_instance_placement
- [ ] modify_ipam
- [ ] modify_ipam_pool
- [ ] modify_ipam_resource_cidr
- [ ] modify_ipam_scope
- [ ] modify_launch_template
- [X] modify_managed_prefix_list
- [X] modify_network_interface_attribute
- [ ] modify_private_dns_name_options
- [ ] modify_reserved_instances
- [ ] modify_security_group_rules
- [ ] modify_snapshot_attribute
- [ ] modify_snapshot_tier
- [X] modify_spot_fleet_request
- [X] modify_subnet_attribute
- [ ] modify_traffic_mirror_filter_network_services
- [ ] modify_traffic_mirror_filter_rule
- [ ] modify_traffic_mirror_session
- [X] modify_transit_gateway
- [ ] modify_transit_gateway_prefix_list_reference
- [X] modify_transit_gateway_vpc_attachment
- [ ] modify_volume
- [ ] modify_volume_attribute
- [X] modify_vpc_attribute
- [ ] modify_vpc_endpoint
- [ ] modify_vpc_endpoint_connection_notification
- [X] modify_vpc_endpoint_service_configuration
  
        The following parameters are not yet implemented: RemovePrivateDnsName
        

- [ ] modify_vpc_endpoint_service_payer_responsibility
- [X] modify_vpc_endpoint_service_permissions
- [X] modify_vpc_peering_connection_options
- [X] modify_vpc_tenancy
- [ ] modify_vpn_connection
- [ ] modify_vpn_connection_options
- [ ] modify_vpn_tunnel_certificate
- [ ] modify_vpn_tunnel_options
- [ ] monitor_instances
- [ ] move_address_to_vpc
- [ ] move_byoip_cidr_to_ipam
- [ ] provision_byoip_cidr
- [ ] provision_ipam_pool_cidr
- [ ] provision_public_ipv4_pool_cidr
- [ ] purchase_host_reservation
- [ ] purchase_reserved_instances_offering
- [ ] purchase_scheduled_instances
- [X] reboot_instances
- [X] register_image
- [ ] register_instance_event_notification_attributes
- [ ] register_transit_gateway_multicast_group_members
- [ ] register_transit_gateway_multicast_group_sources
- [ ] reject_transit_gateway_multicast_domain_associations
- [X] reject_transit_gateway_peering_attachment
- [ ] reject_transit_gateway_vpc_attachment
- [ ] reject_vpc_endpoint_connections
- [X] reject_vpc_peering_connection
- [X] release_address
- [ ] release_hosts
- [ ] release_ipam_pool_allocation
- [X] replace_iam_instance_profile_association
- [X] replace_network_acl_association
- [X] replace_network_acl_entry
- [X] replace_route
- [X] replace_route_table_association
- [ ] replace_transit_gateway_route
- [ ] report_instance_status
- [X] request_spot_fleet
- [X] request_spot_instances
- [ ] reset_address_attribute
- [ ] reset_ebs_default_kms_key_id
- [ ] reset_fpga_image_attribute
- [ ] reset_image_attribute
- [ ] reset_instance_attribute
- [ ] reset_network_interface_attribute
- [ ] reset_snapshot_attribute
- [ ] restore_address_to_classic
- [ ] restore_image_from_recycle_bin
- [ ] restore_managed_prefix_list_version
- [ ] restore_snapshot_from_recycle_bin
- [ ] restore_snapshot_tier
- [ ] revoke_client_vpn_ingress
- [X] revoke_security_group_egress
- [X] revoke_security_group_ingress
- [X] run_instances
  
        The Placement-parameter is validated to verify the availability-zone exists for the current region.

        The InstanceType-parameter can be validated, to see if it is a known instance-type.
        Enable this validation by setting the environment variable `MOTO_EC2_ENABLE_INSTANCE_TYPE_VALIDATION=true`

        The ImageId-parameter can be validated, to see if it is a known AMI.
        Enable this validation by setting the environment variable `MOTO_ENABLE_AMI_VALIDATION=true`

        The KeyPair-parameter can be validated, to see if it is a known key-pair.
        Enable this validation by setting the environment variable `MOTO_ENABLE_KEYPAIR_VALIDATION=true`
        

- [ ] run_scheduled_instances
- [ ] search_local_gateway_routes
- [ ] search_transit_gateway_multicast_groups
- [X] search_transit_gateway_routes
  
        The following filters are currently supported: type, state, route-search.exact-match
        

- [ ] send_diagnostic_interrupt
- [X] start_instances
- [ ] start_network_insights_access_scope_analysis
- [ ] start_network_insights_analysis
- [ ] start_vpc_endpoint_service_private_dns_verification
- [X] stop_instances
- [ ] terminate_client_vpn_connections
- [X] terminate_instances
- [X] unassign_ipv6_addresses
- [X] unassign_private_ip_addresses
- [ ] unmonitor_instances
- [X] update_security_group_rule_descriptions_egress
- [X] update_security_group_rule_descriptions_ingress
- [ ] withdraw_byoip_cidr

