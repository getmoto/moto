.. _implementedservice_elbv2:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=====
elbv2
=====

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_elbv2
            def test_elbv2_behaviour:
                boto3.client("elbv2")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] add_listener_certificates
- [ ] add_tags
- [X] create_listener
- [X] create_load_balancer
- [X] create_rule
- [X] create_target_group
- [X] delete_listener
- [X] delete_load_balancer
- [X] delete_rule
- [X] delete_target_group
- [X] deregister_targets
- [ ] describe_account_limits
- [X] describe_listener_certificates
- [X] describe_listeners
- [X] describe_load_balancer_attributes
- [X] describe_load_balancers
- [X] describe_rules
- [ ] describe_ssl_policies
- [ ] describe_tags
- [ ] describe_target_group_attributes
- [X] describe_target_groups
- [X] describe_target_health
- [X] modify_listener
- [X] modify_load_balancer_attributes
- [X] modify_rule
- [X] modify_target_group
- [X] modify_target_group_attributes
- [X] register_targets
- [X] remove_listener_certificates
- [ ] remove_tags
- [X] set_ip_address_type
- [X] set_rule_priorities
- [X] set_security_groups
- [X] set_subnets

