.. _implementedservice_wafv2:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=====
wafv2
=====

.. autoclass:: moto.wafv2.models.WAFV2Backend

|start-h3| Implemented features for this service |end-h3|

- [X] associate_web_acl
  
        Only APIGateway Stages can be associated at the moment.
        

- [ ] check_capacity
- [ ] create_api_key
- [X] create_ip_set
- [ ] create_regex_pattern_set
- [ ] create_rule_group
- [X] create_web_acl
  
        The following parameters are not yet implemented: CustomResponseBodies, CaptchaConfig
        

- [ ] delete_api_key
- [ ] delete_firewall_manager_rule_groups
- [X] delete_ip_set
- [X] delete_logging_configuration
- [ ] delete_permission_policy
- [ ] delete_regex_pattern_set
- [ ] delete_rule_group
- [X] delete_web_acl
  
        The LockToken-parameter is not yet implemented
        

- [ ] describe_all_managed_products
- [ ] describe_managed_products_by_vendor
- [ ] describe_managed_rule_group
- [X] disassociate_web_acl
- [ ] generate_mobile_sdk_release_url
- [ ] get_decrypted_api_key
- [X] get_ip_set
- [X] get_logging_configuration
- [ ] get_managed_rule_set
- [ ] get_mobile_sdk_release
- [ ] get_permission_policy
- [ ] get_rate_based_statement_managed_keys
- [ ] get_regex_pattern_set
- [ ] get_rule_group
- [ ] get_sampled_requests
- [X] get_web_acl
- [X] get_web_acl_for_resource
- [ ] list_api_keys
- [ ] list_available_managed_rule_group_versions
- [ ] list_available_managed_rule_groups
- [X] list_ip_sets
- [X] list_logging_configurations
- [ ] list_managed_rule_sets
- [ ] list_mobile_sdk_releases
- [ ] list_regex_pattern_sets
- [ ] list_resources_for_web_acl
- [X] list_rule_groups
- [X] list_tags_for_resource
  
        Pagination is not yet implemented
        

- [X] list_web_acls
- [X] put_logging_configuration
- [ ] put_managed_rule_set_versions
- [ ] put_permission_policy
- [X] tag_resource
- [X] untag_resource
- [X] update_ip_set
- [ ] update_managed_rule_set_version_expiry_date
- [ ] update_regex_pattern_set
- [ ] update_rule_group
- [X] update_web_acl
  
        The following parameters are not yet implemented: LockToken, CustomResponseBodies, CaptchaConfig
        


