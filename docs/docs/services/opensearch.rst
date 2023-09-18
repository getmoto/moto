.. _implementedservice_opensearch:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
opensearch
==========

.. autoclass:: moto.opensearch.models.OpenSearchServiceBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_opensearch
            def test_opensearch_behaviour:
                boto3.client("opensearch")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] accept_inbound_connection
- [X] add_tags
- [ ] associate_package
- [ ] authorize_vpc_endpoint_access
- [ ] cancel_service_software_update
- [X] create_domain
- [ ] create_outbound_connection
- [ ] create_package
- [ ] create_vpc_endpoint
- [X] delete_domain
- [ ] delete_inbound_connection
- [ ] delete_outbound_connection
- [ ] delete_package
- [ ] delete_vpc_endpoint
- [X] describe_domain
- [ ] describe_domain_auto_tunes
- [ ] describe_domain_change_progress
- [X] describe_domain_config
- [ ] describe_domain_health
- [ ] describe_domain_nodes
- [ ] describe_domains
- [ ] describe_dry_run_progress
- [ ] describe_inbound_connections
- [ ] describe_instance_type_limits
- [ ] describe_outbound_connections
- [ ] describe_packages
- [ ] describe_reserved_instance_offerings
- [ ] describe_reserved_instances
- [ ] describe_vpc_endpoints
- [ ] dissociate_package
- [X] get_compatible_versions
- [ ] get_package_version_history
- [ ] get_upgrade_history
- [ ] get_upgrade_status
- [x] list_domain_names
- [ ] list_domains_for_package
- [ ] list_instance_type_details
- [ ] list_packages_for_domain
- [ ] list_scheduled_actions
- [X] list_tags
- [ ] list_versions
- [ ] list_vpc_endpoint_access
- [ ] list_vpc_endpoints
- [ ] list_vpc_endpoints_for_domain
- [ ] purchase_reserved_instance_offering
- [ ] reject_inbound_connection
- [X] remove_tags
- [ ] revoke_vpc_endpoint_access
- [ ] start_service_software_update
- [X] update_domain_config
- [ ] update_package
- [ ] update_scheduled_action
- [ ] update_vpc_endpoint
- [ ] upgrade_domain

