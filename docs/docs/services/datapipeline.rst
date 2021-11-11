.. _implementedservice_datapipeline:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

============
datapipeline
============



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_datapipeline
            def test_datapipeline_behaviour:
                boto3.client("datapipeline")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] activate_pipeline
- [ ] add_tags
- [X] create_pipeline
- [ ] deactivate_pipeline
- [X] delete_pipeline
- [X] describe_objects
- [X] describe_pipelines
- [ ] evaluate_expression
- [X] get_pipeline_definition
- [X] list_pipelines
- [ ] poll_for_task
- [X] put_pipeline_definition
- [ ] query_objects
- [ ] remove_tags
- [ ] report_task_progress
- [ ] report_task_runner_heartbeat
- [ ] set_status
- [ ] set_task_status
- [ ] validate_pipeline_definition

