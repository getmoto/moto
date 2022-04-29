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
- [ ] delete_application
- [ ] get_application
- [ ] get_job_run
- [X] list_applications
- [ ] list_job_runs
- [ ] list_tags_for_resource
- [ ] start_application
- [ ] start_job_run
- [ ] stop_application
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_application

