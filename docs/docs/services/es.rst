.. _implementedservice_es:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==
es
==

.. autoclass:: moto.es.models.ElasticsearchServiceBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_es
            def test_es_behaviour:
                boto3.client("es")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] accept_inbound_cross_cluster_search_connection
- [ ] add_tags
- [ ] associate_package
- [ ] cancel_elasticsearch_service_software_update
- [X] create_elasticsearch_domain
- [ ] create_outbound_cross_cluster_search_connection
- [ ] create_package
- [X] delete_elasticsearch_domain
- [ ] delete_elasticsearch_service_role
- [ ] delete_inbound_cross_cluster_search_connection
- [ ] delete_outbound_cross_cluster_search_connection
- [ ] delete_package
- [ ] describe_domain_auto_tunes
- [ ] describe_domain_change_progress
- [X] describe_elasticsearch_domain
- [ ] describe_elasticsearch_domain_config
- [ ] describe_elasticsearch_domains
- [ ] describe_elasticsearch_instance_type_limits
- [ ] describe_inbound_cross_cluster_search_connections
- [ ] describe_outbound_cross_cluster_search_connections
- [ ] describe_packages
- [ ] describe_reserved_elasticsearch_instance_offerings
- [ ] describe_reserved_elasticsearch_instances
- [ ] dissociate_package
- [ ] get_compatible_elasticsearch_versions
- [ ] get_package_version_history
- [ ] get_upgrade_history
- [ ] get_upgrade_status
- [X] list_domain_names
  
        The engine-type parameter is not yet supported.
        Pagination is not yet implemented.
        

- [ ] list_domains_for_package
- [ ] list_elasticsearch_instance_types
- [ ] list_elasticsearch_versions
- [ ] list_packages_for_domain
- [ ] list_tags
- [ ] purchase_reserved_elasticsearch_instance_offering
- [ ] reject_inbound_cross_cluster_search_connection
- [ ] remove_tags
- [ ] start_elasticsearch_service_software_update
- [ ] update_elasticsearch_domain_config
- [ ] update_package
- [ ] upgrade_elasticsearch_domain

