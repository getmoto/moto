.. _implementedservice_codepipeline:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

============
codepipeline
============

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_codepipeline
            def test_codepipeline_behaviour:
                boto3.client("codepipeline")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] acknowledge_job
- [ ] acknowledge_third_party_job
- [ ] create_custom_action_type
- [X] create_pipeline
- [ ] delete_custom_action_type
- [X] delete_pipeline
- [ ] delete_webhook
- [ ] deregister_webhook_with_third_party
- [ ] disable_stage_transition
- [ ] enable_stage_transition
- [ ] get_action_type
- [ ] get_job_details
- [X] get_pipeline
- [ ] get_pipeline_execution
- [ ] get_pipeline_state
- [ ] get_third_party_job_details
- [ ] list_action_executions
- [ ] list_action_types
- [ ] list_pipeline_executions
- [X] list_pipelines
- [X] list_tags_for_resource
- [ ] list_webhooks
- [ ] poll_for_jobs
- [ ] poll_for_third_party_jobs
- [ ] put_action_revision
- [ ] put_approval_result
- [ ] put_job_failure_result
- [ ] put_job_success_result
- [ ] put_third_party_job_failure_result
- [ ] put_third_party_job_success_result
- [ ] put_webhook
- [ ] register_webhook_with_third_party
- [ ] retry_stage_execution
- [ ] start_pipeline_execution
- [ ] stop_pipeline_execution
- [X] tag_resource
- [X] untag_resource
- [ ] update_action_type
- [X] update_pipeline

