.. _implementedservice_comprehend:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
comprehend
==========

.. autoclass:: moto.comprehend.models.ComprehendBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_comprehend
            def test_comprehend_behaviour:
                boto3.client("comprehend")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] batch_detect_dominant_language
- [ ] batch_detect_entities
- [ ] batch_detect_key_phrases
- [ ] batch_detect_sentiment
- [ ] batch_detect_syntax
- [ ] batch_detect_targeted_sentiment
- [ ] classify_document
- [ ] contains_pii_entities
- [ ] create_dataset
- [ ] create_document_classifier
- [ ] create_endpoint
- [X] create_entity_recognizer
  
        The ClientRequestToken-parameter is not yet implemented
        

- [ ] create_flywheel
- [ ] delete_document_classifier
- [ ] delete_endpoint
- [X] delete_entity_recognizer
- [ ] delete_flywheel
- [ ] delete_resource_policy
- [ ] describe_dataset
- [ ] describe_document_classification_job
- [ ] describe_document_classifier
- [ ] describe_dominant_language_detection_job
- [ ] describe_endpoint
- [ ] describe_entities_detection_job
- [X] describe_entity_recognizer
- [ ] describe_events_detection_job
- [ ] describe_flywheel
- [ ] describe_flywheel_iteration
- [ ] describe_key_phrases_detection_job
- [ ] describe_pii_entities_detection_job
- [ ] describe_resource_policy
- [ ] describe_sentiment_detection_job
- [ ] describe_targeted_sentiment_detection_job
- [ ] describe_topics_detection_job
- [ ] detect_dominant_language
- [ ] detect_entities
- [X] detect_key_phrases
- [X] detect_pii_entities
- [X] detect_sentiment
- [ ] detect_syntax
- [ ] detect_targeted_sentiment
- [ ] import_model
- [ ] list_datasets
- [ ] list_document_classification_jobs
- [ ] list_document_classifier_summaries
- [ ] list_document_classifiers
- [ ] list_dominant_language_detection_jobs
- [ ] list_endpoints
- [ ] list_entities_detection_jobs
- [ ] list_entity_recognizer_summaries
- [X] list_entity_recognizers
  
        Pagination is not yet implemented.
        The following filters are not yet implemented: Status, SubmitTimeBefore, SubmitTimeAfter
        

- [ ] list_events_detection_jobs
- [ ] list_flywheel_iteration_history
- [ ] list_flywheels
- [ ] list_key_phrases_detection_jobs
- [ ] list_pii_entities_detection_jobs
- [ ] list_sentiment_detection_jobs
- [X] list_tags_for_resource
- [ ] list_targeted_sentiment_detection_jobs
- [ ] list_topics_detection_jobs
- [ ] put_resource_policy
- [ ] start_document_classification_job
- [ ] start_dominant_language_detection_job
- [ ] start_entities_detection_job
- [ ] start_events_detection_job
- [ ] start_flywheel_iteration
- [ ] start_key_phrases_detection_job
- [ ] start_pii_entities_detection_job
- [ ] start_sentiment_detection_job
- [ ] start_targeted_sentiment_detection_job
- [ ] start_topics_detection_job
- [ ] stop_dominant_language_detection_job
- [ ] stop_entities_detection_job
- [ ] stop_events_detection_job
- [ ] stop_key_phrases_detection_job
- [ ] stop_pii_entities_detection_job
- [ ] stop_sentiment_detection_job
- [ ] stop_targeted_sentiment_detection_job
- [ ] stop_training_document_classifier
- [X] stop_training_entity_recognizer
- [X] tag_resource
- [X] untag_resource
- [ ] update_endpoint
- [ ] update_flywheel

