.. _implementedservice_rekognition:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===========
rekognition
===========

.. autoclass:: moto.rekognition.models.RekognitionBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_rekognition
            def test_rekognition_behaviour:
                boto3.client("rekognition")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] compare_faces
- [ ] create_collection
- [ ] create_dataset
- [ ] create_project
- [ ] create_project_version
- [ ] create_stream_processor
- [ ] delete_collection
- [ ] delete_dataset
- [ ] delete_faces
- [ ] delete_project
- [ ] delete_project_version
- [ ] delete_stream_processor
- [ ] describe_collection
- [ ] describe_dataset
- [ ] describe_project_versions
- [ ] describe_projects
- [ ] describe_stream_processor
- [ ] detect_custom_labels
- [ ] detect_faces
- [ ] detect_labels
- [ ] detect_moderation_labels
- [ ] detect_protective_equipment
- [ ] detect_text
- [ ] distribute_dataset_entries
- [ ] get_celebrity_info
- [ ] get_celebrity_recognition
- [ ] get_content_moderation
- [ ] get_face_detection
- [X] get_face_search
  
        This returns hardcoded values and none of the parameters are taken into account.
        

- [ ] get_label_detection
- [ ] get_person_tracking
- [ ] get_segment_detection
- [X] get_text_detection
  
        This returns hardcoded values and none of the parameters are taken into account.
        

- [ ] index_faces
- [ ] list_collections
- [ ] list_dataset_entries
- [ ] list_dataset_labels
- [ ] list_faces
- [ ] list_stream_processors
- [ ] list_tags_for_resource
- [ ] recognize_celebrities
- [ ] search_faces
- [ ] search_faces_by_image
- [ ] start_celebrity_recognition
- [ ] start_content_moderation
- [ ] start_face_detection
- [X] start_face_search
- [ ] start_label_detection
- [ ] start_person_tracking
- [ ] start_project_version
- [ ] start_segment_detection
- [ ] start_stream_processor
- [X] start_text_detection
- [ ] stop_project_version
- [ ] stop_stream_processor
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_dataset_entries
- [ ] update_stream_processor

