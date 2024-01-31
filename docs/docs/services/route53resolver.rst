.. _implementedservice_route53resolver:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===============
route53resolver
===============

.. autoclass:: moto.route53resolver.models.Route53ResolverBackend

|start-h3| Implemented features for this service |end-h3|

- [ ] associate_firewall_rule_group
- [X] associate_resolver_endpoint_ip_address
- [ ] associate_resolver_query_log_config
- [X] associate_resolver_rule
- [ ] create_firewall_domain_list
- [ ] create_firewall_rule
- [ ] create_firewall_rule_group
- [ ] create_outpost_resolver
- [X] create_resolver_endpoint
  
        Return description for a newly created resolver endpoint.

        NOTE:  IPv6 IPs are currently not being filtered when
        calculating the create_resolver_endpoint() IpAddresses.
        

- [ ] create_resolver_query_log_config
- [X] create_resolver_rule
  Return description for a newly created resolver rule.

- [ ] delete_firewall_domain_list
- [ ] delete_firewall_rule
- [ ] delete_firewall_rule_group
- [ ] delete_outpost_resolver
- [X] delete_resolver_endpoint
- [ ] delete_resolver_query_log_config
- [X] delete_resolver_rule
- [ ] disassociate_firewall_rule_group
- [X] disassociate_resolver_endpoint_ip_address
- [ ] disassociate_resolver_query_log_config
- [X] disassociate_resolver_rule
- [ ] get_firewall_config
- [ ] get_firewall_domain_list
- [ ] get_firewall_rule_group
- [ ] get_firewall_rule_group_association
- [ ] get_firewall_rule_group_policy
- [ ] get_outpost_resolver
- [ ] get_resolver_config
- [ ] get_resolver_dnssec_config
- [X] get_resolver_endpoint
- [ ] get_resolver_query_log_config
- [ ] get_resolver_query_log_config_association
- [ ] get_resolver_query_log_config_policy
- [X] get_resolver_rule
  Return info for specified resolver rule.

- [X] get_resolver_rule_association
- [ ] get_resolver_rule_policy
- [ ] import_firewall_domains
- [ ] list_firewall_configs
- [ ] list_firewall_domain_lists
- [ ] list_firewall_domains
- [ ] list_firewall_rule_group_associations
- [ ] list_firewall_rule_groups
- [ ] list_firewall_rules
- [ ] list_outpost_resolvers
- [ ] list_resolver_configs
- [ ] list_resolver_dnssec_configs
- [X] list_resolver_endpoint_ip_addresses
- [X] list_resolver_endpoints
- [ ] list_resolver_query_log_config_associations
- [ ] list_resolver_query_log_configs
- [X] list_resolver_rule_associations
- [X] list_resolver_rules
- [X] list_tags_for_resource
- [ ] put_firewall_rule_group_policy
- [ ] put_resolver_query_log_config_policy
- [ ] put_resolver_rule_policy
- [X] tag_resource
- [X] untag_resource
- [ ] update_firewall_config
- [ ] update_firewall_domains
- [ ] update_firewall_rule
- [ ] update_firewall_rule_group_association
- [ ] update_outpost_resolver
- [ ] update_resolver_config
- [ ] update_resolver_dnssec_config
- [X] update_resolver_endpoint
- [ ] update_resolver_rule

