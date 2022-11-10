.. _implementedservice_elastictranscoder:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=================
elastictranscoder
=================

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_elastictranscoder
            def test_elastictranscoder_behaviour:
                boto3.client("elastictranscoder")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] cancel_job
- [ ] create_job
- [X] create_pipeline
  
        The following parameters are not yet implemented:
        AWSKMSKeyArn, Notifications
        

- [ ] create_preset
- [X] delete_pipeline
- [ ] delete_preset
- [ ] list_jobs_by_pipeline
- [ ] list_jobs_by_status
- [X] list_pipelines
- [ ] list_presets
- [ ] read_job
- [X] read_pipeline
- [ ] read_preset
- [ ] test_role
- [X] update_pipeline
  
        The following parameters are not yet implemented:
        AWSKMSKeyArn, Notifications, ContentConfig, ThumbnailConfig
        

- [ ] update_pipeline_notifications
- [ ] update_pipeline_status

