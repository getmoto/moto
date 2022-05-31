.. _implementedservice_elb:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
elb
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_elb
            def test_elb_behaviour:
                boto3.client("elb")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_tags
- [X] apply_security_groups_to_load_balancer
- [X] attach_load_balancer_to_subnets
- [X] configure_health_check
- [X] create_app_cookie_stickiness_policy
- [X] create_lb_cookie_stickiness_policy
- [X] create_load_balancer
- [X] create_load_balancer_listeners
- [ ] create_load_balancer_policy
- [X] delete_load_balancer
- [X] delete_load_balancer_listeners
- [X] delete_load_balancer_policy
- [ ] deregister_instances_from_load_balancer
- [ ] describe_account_limits
- [X] describe_instance_health
- [ ] describe_load_balancer_attributes
- [X] describe_load_balancer_policies
- [ ] describe_load_balancer_policy_types
- [X] describe_load_balancers
- [ ] describe_tags
- [X] detach_load_balancer_from_subnets
- [X] disable_availability_zones_for_load_balancer
- [X] enable_availability_zones_for_load_balancer
- [X] modify_load_balancer_attributes
- [ ] register_instances_with_load_balancer
- [ ] remove_tags
- [X] set_load_balancer_listener_ssl_certificate
- [ ] set_load_balancer_policies_for_backend_server
- [X] set_load_balancer_policies_of_listener

