.. _implementedservice_wafv2:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=====
wafv2
=====

.. autoclass:: moto.wafv2.models.WAFV2Backend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_wafv2
            def test_wafv2_behaviour:
                boto3.client("wafv2")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] associate_web_acl
- [ ] check_capacity
- [ ] create_ip_set
- [ ] create_regex_pattern_set
- [ ] create_rule_group
- [X] create_web_acl
- [ ] delete_firewall_manager_rule_groups
- [ ] delete_ip_set
- [ ] delete_logging_configuration
- [ ] delete_permission_policy
- [ ] delete_regex_pattern_set
- [ ] delete_rule_group
- [ ] delete_web_acl
- [ ] describe_managed_rule_group
- [ ] disassociate_web_acl
- [ ] get_ip_set
- [ ] get_logging_configuration
- [ ] get_managed_rule_set
- [ ] get_permission_policy
- [ ] get_rate_based_statement_managed_keys
- [ ] get_regex_pattern_set
- [ ] get_rule_group
- [ ] get_sampled_requests
- [ ] get_web_acl
- [ ] get_web_acl_for_resource
- [ ] list_available_managed_rule_group_versions
- [ ] list_available_managed_rule_groups
- [ ] list_ip_sets
- [ ] list_logging_configurations
- [ ] list_managed_rule_sets
- [ ] list_regex_pattern_sets
- [ ] list_resources_for_web_acl
- [ ] list_rule_groups
- [ ] list_tags_for_resource
- [X] list_web_acls
- [ ] put_logging_configuration
- [ ] put_managed_rule_set_versions
- [ ] put_permission_policy
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_ip_set
- [ ] update_managed_rule_set_version_expiry_date
- [ ] update_regex_pattern_set
- [ ] update_rule_group
- [ ] update_web_acl

