.. _implementedservice_stepfunctions:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=============
stepfunctions
=============

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_stepfunctions
            def test_stepfunctions_behaviour:
                boto3.client("stepfunctions")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] create_activity
- [X] create_state_machine
- [ ] delete_activity
- [X] delete_state_machine
- [ ] describe_activity
- [X] describe_execution
- [ ] describe_map_run
- [X] describe_state_machine
- [ ] describe_state_machine_for_execution
- [ ] get_activity_task
- [X] get_execution_history
- [ ] list_activities
- [X] list_executions
- [ ] list_map_runs
- [X] list_state_machines
- [X] list_tags_for_resource
- [ ] send_task_failure
- [ ] send_task_heartbeat
- [ ] send_task_success
- [X] start_execution
- [ ] start_sync_execution
- [X] stop_execution
- [X] tag_resource
- [X] untag_resource
- [ ] update_map_run
- [X] update_state_machine

