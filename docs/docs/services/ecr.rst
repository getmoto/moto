.. _implementedservice_ecr:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
ecr
===

|start-h3| Implemented features for this service |end-h3|

- [ ] batch_check_layer_availability
- [X] batch_delete_image
- [X] batch_get_image
  
        The parameter AcceptedMediaTypes has not yet been implemented
        

- [X] batch_get_repository_scanning_configuration
- [ ] complete_layer_upload
- [ ] create_pull_through_cache_rule
- [X] create_repository
- [ ] create_repository_creation_template
- [X] delete_lifecycle_policy
- [ ] delete_pull_through_cache_rule
- [X] delete_registry_policy
- [X] delete_repository
- [ ] delete_repository_creation_template
- [X] delete_repository_policy
- [ ] describe_image_replication_status
- [X] describe_image_scan_findings
  
        This operation will return a static result by default. It is possible to configure a custom result using the Moto API.

        Here is some example code showing how this can be configured:

        .. sourcecode:: python

            # Dict with the exact response that you want to Moto to return
            example_response = {
                "imageScanFindings": {
                    "enhancedFindings": [
                    ],
                    "findingSeverityCounts": {
                        "MEDIUM": 1,
                        "UNTRIAGED": 1
                    }
                },
                "registryId": 000000000000,
                "repositoryName": "reponame",
                "imageId": {
                    "imageTag": "latest"
                },
                "imageScanStatus": {
                    "status": "COMPLETE",
                    "description": "The scan was completed successfully."
                }
            }
            findings = {
                "results": [example_response],
                # Specify a region - us-east-1 by default
                "region": "us-west-1",
            }
            resp = requests.post(
                "http://motoapi.amazonaws.com/moto-api/static/ecr/scan-finding-results",
                json=findings,
            )

            ecr = boto3.client("ecr", region_name="us-west-1")
            # Create an image and start a scan
            # ...
            # Return the findings for reponame:latest
            findings = ecr.describe_image_scan_findings(
                repositoryName="reponame", imageId={"imageTag": "latest"}
            )
            findings.pop("ResponseMetadata")
            assert findings == example_response

        Note that the repository-name and imageTag/imageDigest should be an exact match. If you call `describe_image_scan_findings` with a repository/imageTag that is not part of any of the custom results, Moto will return a static default response.

        

- [X] describe_images
- [ ] describe_pull_through_cache_rules
- [X] describe_registry
- [X] describe_repositories
  
        maxResults and nextToken not implemented
        

- [ ] describe_repository_creation_templates
- [ ] get_account_setting
- [ ] get_authorization_token
- [ ] get_download_url_for_layer
- [X] get_lifecycle_policy
- [ ] get_lifecycle_policy_preview
- [X] get_registry_policy
- [X] get_registry_scanning_configuration
- [X] get_repository_policy
- [ ] initiate_layer_upload
- [X] list_images
  
        maxResults and filtering not implemented
        

- [X] list_tags_for_resource
- [ ] put_account_setting
- [X] put_image
- [X] put_image_scanning_configuration
- [X] put_image_tag_mutability
- [X] put_lifecycle_policy
- [X] put_registry_policy
- [X] put_registry_scanning_configuration
- [X] put_replication_configuration
- [X] set_repository_policy
- [X] start_image_scan
- [ ] start_lifecycle_policy_preview
- [X] tag_resource
- [X] untag_resource
- [ ] update_pull_through_cache_rule
- [ ] update_repository_creation_template
- [ ] upload_layer_part
- [ ] validate_pull_through_cache_rule

