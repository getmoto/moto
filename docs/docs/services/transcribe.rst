.. _implementedservice_transcribe:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
transcribe
==========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_transcribe
            def test_transcribe_behaviour:
                boto3.client("transcribe")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] create_call_analytics_category
- [ ] create_language_model
- [X] create_medical_vocabulary
- [X] create_vocabulary
- [ ] create_vocabulary_filter
- [ ] delete_call_analytics_category
- [ ] delete_call_analytics_job
- [ ] delete_language_model
- [X] delete_medical_transcription_job
- [X] delete_medical_vocabulary
- [X] delete_transcription_job
- [X] delete_vocabulary
- [ ] delete_vocabulary_filter
- [ ] describe_language_model
- [ ] get_call_analytics_category
- [ ] get_call_analytics_job
- [X] get_medical_transcription_job
- [X] get_medical_vocabulary
- [X] get_transcription_job
- [X] get_vocabulary
- [ ] get_vocabulary_filter
- [ ] list_call_analytics_categories
- [ ] list_call_analytics_jobs
- [ ] list_language_models
- [X] list_medical_transcription_jobs
- [X] list_medical_vocabularies
- [ ] list_tags_for_resource
- [X] list_transcription_jobs
- [X] list_vocabularies
- [ ] list_vocabulary_filters
- [ ] start_call_analytics_job
- [X] start_medical_transcription_job
- [X] start_transcription_job
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_call_analytics_category
- [ ] update_medical_vocabulary
- [ ] update_vocabulary
- [ ] update_vocabulary_filter

