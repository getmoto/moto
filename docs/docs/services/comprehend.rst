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
- [ ] delete_resource_policy
- [ ] describe_dataset
- [ ] describe_document_classification_job
- [X] describe_document_classifier
- [ ] describe_dominant_language_detection_job
- [X] describe_endpoint
- [ ] describe_entities_detection_job
- [X] describe_entity_recognizer
- [ ] describe_events_detection_job
- [X] describe_flywheel
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
- [ ] detect_toxic_content
- [ ] import_model
- [ ] list_datasets
- [ ] list_document_classification_jobs
- [ ] list_document_classifier_summaries
- [X] list_document_classifiers
  
List document classifiers with optional filtering.
Pagination is not yet implemented.


- [ ] list_dominant_language_detection_jobs
- [X] list_endpoints
  
List endpoints with optional filtering.
Pagination is not yet implemented.


- [ ] list_entities_detection_jobs
- [ ] list_entity_recognizer_summaries
- [X] list_entity_recognizers
  
Pagination is not yet implemented.
The following filters are not yet implemented: Status, SubmitTimeBefore, SubmitTimeAfter


- [ ] list_events_detection_jobs
- [ ] list_flywheel_iteration_history
- [X] list_flywheels
  
List flywheels with optional filtering.
Pagination is not yet implemented.


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
- [X] start_flywheel_iteration
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
- [X] stop_training_document_classifier
- [X] stop_training_entity_recognizer
- [X] tag_resource
- [X] untag_resource
- [X] update_endpoint
- [ ] update_flywheel

