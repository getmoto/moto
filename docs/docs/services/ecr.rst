.. _implementedservice_ecr:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
ecr
===



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_ecr
            def test_ecr_behaviour:
                boto3.client("ecr")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] batch_check_layer_availability
- [X] batch_delete_image
- [X] batch_get_image
- [ ] complete_layer_upload
- [X] create_repository
- [X] delete_lifecycle_policy
- [X] delete_registry_policy
- [X] delete_repository
- [X] delete_repository_policy
- [ ] describe_image_replication_status
- [X] describe_image_scan_findings
- [X] describe_images
- [X] describe_registry
- [X] describe_repositories
  
        maxResults and nextToken not implemented
        

- [ ] get_authorization_token
- [ ] get_download_url_for_layer
- [X] get_lifecycle_policy
- [ ] get_lifecycle_policy_preview
- [X] get_registry_policy
- [X] get_repository_policy
- [ ] initiate_layer_upload
- [X] list_images
  
        maxResults and filtering not implemented
        

- [X] list_tags_for_resource
- [X] put_image
- [X] put_image_scanning_configuration
- [X] put_image_tag_mutability
- [X] put_lifecycle_policy
- [X] put_registry_policy
- [X] put_replication_configuration
- [X] set_repository_policy
- [X] start_image_scan
- [ ] start_lifecycle_policy_preview
- [X] tag_resource
- [X] untag_resource
- [ ] upload_layer_part

