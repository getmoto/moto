.. _implementedservice_application-autoscaling:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=======================
application-autoscaling
=======================

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_applicationautoscaling
            def test_applicationautoscaling_behaviour:
                boto3.client("application-autoscaling")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] delete_scaling_policy
- [X] delete_scheduled_action
- [X] deregister_scalable_target
  Registers or updates a scalable target.

- [X] describe_scalable_targets
  Describe scalable targets.

- [ ] describe_scaling_activities
- [X] describe_scaling_policies
- [X] describe_scheduled_actions
  
        Pagination is not yet implemented
        

- [X] put_scaling_policy
- [X] put_scheduled_action
- [X] register_scalable_target
  Registers or updates a scalable target.


