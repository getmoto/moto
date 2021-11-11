.. _implementedservice_autoscaling:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===========
autoscaling
===========



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_autoscaling
            def test_autoscaling_behaviour:
                boto3.client("autoscaling")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] attach_instances
- [X] attach_load_balancer_target_groups
- [X] attach_load_balancers
- [ ] batch_delete_scheduled_action
- [ ] batch_put_scheduled_update_group_action
- [ ] cancel_instance_refresh
- [ ] complete_lifecycle_action
- [X] create_auto_scaling_group
- [X] create_launch_configuration
- [X] create_or_update_tags
- [X] delete_auto_scaling_group
- [X] delete_launch_configuration
- [X] delete_lifecycle_hook
- [ ] delete_notification_configuration
- [X] delete_policy
- [ ] delete_scheduled_action
- [X] delete_tags
- [ ] delete_warm_pool
- [ ] describe_account_limits
- [ ] describe_adjustment_types
- [X] describe_auto_scaling_groups
- [X] describe_auto_scaling_instances
- [ ] describe_auto_scaling_notification_types
- [ ] describe_instance_refreshes
- [X] describe_launch_configurations
- [ ] describe_lifecycle_hook_types
- [X] describe_lifecycle_hooks
- [X] describe_load_balancer_target_groups
- [X] describe_load_balancers
- [ ] describe_metric_collection_types
- [ ] describe_notification_configurations
- [X] describe_policies
- [ ] describe_scaling_activities
- [ ] describe_scaling_process_types
- [ ] describe_scheduled_actions
- [ ] describe_tags
- [ ] describe_termination_policy_types
- [ ] describe_warm_pool
- [X] detach_instances
- [X] detach_load_balancer_target_groups
- [X] detach_load_balancers
- [ ] disable_metrics_collection
- [ ] enable_metrics_collection
- [ ] enter_standby
- [X] execute_policy
- [ ] exit_standby
- [ ] get_predictive_scaling_forecast
- [ ] put_lifecycle_hook
- [ ] put_notification_configuration
- [ ] put_scaling_policy
- [ ] put_scheduled_update_group_action
- [ ] put_warm_pool
- [ ] record_lifecycle_action_heartbeat
- [X] resume_processes
- [X] set_desired_capacity
- [X] set_instance_health
- [X] set_instance_protection
- [ ] start_instance_refresh
- [X] suspend_processes
- [ ] terminate_instance_in_auto_scaling_group
- [X] update_auto_scaling_group

