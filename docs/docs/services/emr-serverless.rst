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

- [X] cancel_job_run
- [X] create_application
- [X] delete_application
- [X] get_application
- [X] get_job_run
- [X] list_applications
- [X] list_job_runs
- [ ] list_tags_for_resource
- [X] start_application
- [X] start_job_run
- [X] stop_application
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_application

