.. _implementedservice_comprehend:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
comprehend
==========

.. autoclass:: moto.comprehend.models.ComprehendBackend

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
- [X] create_document_classifier
- [X] create_endpoint
- [X] create_entity_recognizer
  
        The ClientRequestToken-parameter is not yet implemented
        

- [X] create_flywheel
- [X] delete_document_classifier
- [X] delete_endpoint
- [X] delete_entity_recognizer
- [X] delete_flywheel
- [X] delete_resource_policy
  
        The PolicyRevisionId-parameter for conditional deletion is not yet implemented.
        

- [ ] describe_dataset
- [X] describe_document_classification_job
- [X] describe_document_classifier
- [X] describe_dominant_language_detection_job
- [X] describe_endpoint
- [X] describe_entities_detection_job
- [X] describe_entity_recognizer
- [X] describe_events_detection_job
- [X] describe_flywheel
- [ ] describe_flywheel_iteration
- [X] describe_key_phrases_detection_job
- [X] describe_pii_entities_detection_job
- [X] describe_resource_policy
- [X] describe_sentiment_detection_job
- [X] describe_targeted_sentiment_detection_job
- [X] describe_topics_detection_job
- [ ] detect_dominant_language
- [ ] detect_entities
- [X] detect_key_phrases
- [X] detect_pii_entities
- [X] detect_sentiment
- [ ] detect_syntax
- [ ] detect_targeted_sentiment
- [ ] detect_toxic_content
- [ ] import_model
- [ ] list_datasets
- [X] list_document_classification_jobs
- [ ] list_document_classifier_summaries
- [X] list_document_classifiers
  
        List document classifiers with optional filtering.
        Pagination is not yet implemented.
        

- [X] list_dominant_language_detection_jobs
- [X] list_endpoints
  
        List endpoints with optional filtering.
        Pagination is not yet implemented.
        

- [X] list_entities_detection_jobs
- [ ] list_entity_recognizer_summaries
- [X] list_entity_recognizers
  
        Pagination is not yet implemented.
        The following filters are not yet implemented: Status, SubmitTimeBefore, SubmitTimeAfter
        

- [X] list_events_detection_jobs
- [ ] list_flywheel_iteration_history
- [X] list_flywheels
  
        List flywheels with optional filtering.
        Pagination is not yet implemented.
        

- [X] list_key_phrases_detection_jobs
- [X] list_pii_entities_detection_jobs
- [X] list_sentiment_detection_jobs
- [X] list_tags_for_resource
- [X] list_targeted_sentiment_detection_jobs
- [X] list_topics_detection_jobs
- [X] put_resource_policy
  
        The PolicyRevisionId-parameter for conditional updates is not yet implemented.
        A check for whether the resource itself exists is also not yet implemented.
        

- [X] start_document_classification_job
- [X] start_dominant_language_detection_job
- [X] start_entities_detection_job
- [X] start_events_detection_job
- [X] start_flywheel_iteration
- [X] start_key_phrases_detection_job
- [X] start_pii_entities_detection_job
- [X] start_sentiment_detection_job
- [X] start_targeted_sentiment_detection_job
- [X] start_topics_detection_job
- [X] stop_dominant_language_detection_job
- [X] stop_entities_detection_job
- [X] stop_events_detection_job
- [X] stop_key_phrases_detection_job
- [X] stop_pii_entities_detection_job
- [X] stop_sentiment_detection_job
- [X] stop_targeted_sentiment_detection_job
- [X] stop_training_document_classifier
- [X] stop_training_entity_recognizer
- [X] tag_resource
- [X] untag_resource
- [X] update_endpoint
- [ ] update_flywheel

