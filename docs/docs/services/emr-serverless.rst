.. _implementedservice_emr-serverless:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==============
emr-serverless
==============

.. autoclass:: moto.emrserverless.models.EMRServerlessBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_emrserverless
            def test_emrserverless_behaviour:
                boto3.client("emr-serverless")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] cancel_job_run
- [X] create_application
- [X] delete_application
- [X] get_application
- [ ] get_dashboard_for_job_run
- [ ] get_job_run
- [X] list_applications
- [ ] list_job_runs
- [ ] list_tags_for_resource
- [X] start_application
- [ ] start_job_run
- [X] stop_application
- [ ] tag_resource
- [ ] untag_resource
- [X] update_application

