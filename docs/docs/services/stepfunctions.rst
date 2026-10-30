.. _implementedservice_stepfunctions:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=============
stepfunctions
=============

.. autoclass:: moto.stepfunctions.models.StepFunctionBackend

|start-h3| Implemented features for this service |end-h3|

- [X] create_activity
- [X] create_state_machine
- [X] create_state_machine_alias
- [X] delete_activity
- [X] delete_state_machine
- [X] delete_state_machine_alias
- [ ] delete_state_machine_version
- [X] describe_activity
- [X] describe_execution
- [X] describe_map_run
- [X] describe_state_machine
- [X] describe_state_machine_alias
- [X] describe_state_machine_for_execution
- [ ] get_activity_task
- [X] get_execution_history
- [X] list_activities
- [X] list_executions
- [X] list_map_runs
- [X] list_state_machine_aliases
- [ ] list_state_machine_versions
- [X] list_state_machines
- [X] list_tags_for_resource
- [ ] publish_state_machine_version
- [ ] redrive_execution
- [X] send_task_failure
- [X] send_task_heartbeat
- [X] send_task_success
- [X] start_execution
- [X] start_sync_execution
  
        Only EXPRESS state machines are supported, as on AWS. The execution
        completes immediately: its status follows SF_EXECUTION_HISTORY_TYPE
        (SUCCEEDED, or FAILED when set to FAILURE). As with StartExecution, the
        definition is not run; enable the parser for real outputs. Synchronous
        Express executions are not stored, so DescribeExecution cannot find them.

        In ServerMode, create the client with
        `botocore.config.Config(inject_host_prefix=False)`: the operation's
        endpoint has the host prefix "sync-", which would otherwise be added
        to the server's host name.
        

- [X] stop_execution
- [X] tag_resource
- [ ] test_state
- [X] untag_resource
- [X] update_map_run
- [X] update_state_machine
- [X] update_state_machine_alias
- [ ] validate_state_machine_definition

