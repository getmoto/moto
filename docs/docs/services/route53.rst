.. _implementedservice_route53:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=======
route53
=======

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_route53
            def test_route53_behaviour:
                boto3.client("route53")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] activate_key_signing_key
- [ ] associate_vpc_with_hosted_zone
- [ ] change_cidr_collection
- [X] change_resource_record_sets
- [X] change_tags_for_resource
- [ ] create_cidr_collection
- [X] create_health_check
- [X] create_hosted_zone
- [ ] create_key_signing_key
- [X] create_query_logging_config
  Process the create_query_logging_config request.

- [X] create_reusable_delegation_set
- [ ] create_traffic_policy
- [ ] create_traffic_policy_instance
- [ ] create_traffic_policy_version
- [ ] create_vpc_association_authorization
- [ ] deactivate_key_signing_key
- [ ] delete_cidr_collection
- [X] delete_health_check
- [X] delete_hosted_zone
- [ ] delete_key_signing_key
- [X] delete_query_logging_config
  Delete query logging config, if it exists.

- [X] delete_reusable_delegation_set
- [ ] delete_traffic_policy
- [ ] delete_traffic_policy_instance
- [ ] delete_vpc_association_authorization
- [ ] disable_hosted_zone_dnssec
- [ ] disassociate_vpc_from_hosted_zone
- [ ] enable_hosted_zone_dnssec
- [ ] get_account_limit
- [ ] get_change
- [ ] get_checker_ip_ranges
- [X] get_dnssec
- [ ] get_geo_location
- [X] get_health_check
- [ ] get_health_check_count
- [ ] get_health_check_last_failure_reason
- [ ] get_health_check_status
- [X] get_hosted_zone
- [X] get_hosted_zone_count
- [ ] get_hosted_zone_limit
- [X] get_query_logging_config
  Return query logging config, if it exists.

- [X] get_reusable_delegation_set
- [ ] get_reusable_delegation_set_limit
- [ ] get_traffic_policy
- [ ] get_traffic_policy_instance
- [ ] get_traffic_policy_instance_count
- [ ] list_cidr_blocks
- [ ] list_cidr_collections
- [ ] list_cidr_locations
- [ ] list_geo_locations
- [X] list_health_checks
- [X] list_hosted_zones
- [X] list_hosted_zones_by_name
- [X] list_hosted_zones_by_vpc
  
        Pagination is not yet implemented
        

- [X] list_query_logging_configs
  Return a list of query logging configs.

- [X] list_resource_record_sets
  
        The StartRecordIdentifier-parameter is not yet implemented
        

- [X] list_reusable_delegation_sets
  
        Pagination is not yet implemented
        

- [X] list_tags_for_resource
- [ ] list_tags_for_resources
- [ ] list_traffic_policies
- [ ] list_traffic_policy_instances
- [ ] list_traffic_policy_instances_by_hosted_zone
- [ ] list_traffic_policy_instances_by_policy
- [ ] list_traffic_policy_versions
- [ ] list_vpc_association_authorizations
- [ ] test_dns_answer
- [ ] update_health_check
- [ ] update_hosted_zone_comment
- [ ] update_traffic_policy_comment
- [ ] update_traffic_policy_instance

