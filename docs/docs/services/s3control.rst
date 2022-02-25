.. _implementedservice_s3control:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=========
s3control
=========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_s3control
            def test_s3control_behaviour:
                boto3.client("s3control")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_access_point
- [ ] create_access_point_for_object_lambda
- [ ] create_bucket
- [ ] create_job
- [ ] create_multi_region_access_point
- [X] delete_access_point
- [ ] delete_access_point_for_object_lambda
- [X] delete_access_point_policy
- [ ] delete_access_point_policy_for_object_lambda
- [ ] delete_bucket
- [ ] delete_bucket_lifecycle_configuration
- [ ] delete_bucket_policy
- [ ] delete_bucket_tagging
- [ ] delete_job_tagging
- [ ] delete_multi_region_access_point
- [X] delete_public_access_block
- [ ] delete_storage_lens_configuration
- [ ] delete_storage_lens_configuration_tagging
- [ ] describe_job
- [ ] describe_multi_region_access_point_operation
- [X] get_access_point
- [ ] get_access_point_configuration_for_object_lambda
- [ ] get_access_point_for_object_lambda
- [X] get_access_point_policy
- [ ] get_access_point_policy_for_object_lambda
- [X] get_access_point_policy_status
  
        We assume the policy status is always public
        

- [ ] get_access_point_policy_status_for_object_lambda
- [ ] get_bucket
- [ ] get_bucket_lifecycle_configuration
- [ ] get_bucket_policy
- [ ] get_bucket_tagging
- [ ] get_job_tagging
- [ ] get_multi_region_access_point
- [ ] get_multi_region_access_point_policy
- [ ] get_multi_region_access_point_policy_status
- [X] get_public_access_block
- [ ] get_storage_lens_configuration
- [ ] get_storage_lens_configuration_tagging
- [ ] list_access_points
- [ ] list_access_points_for_object_lambda
- [ ] list_jobs
- [ ] list_multi_region_access_points
- [ ] list_regional_buckets
- [ ] list_storage_lens_configurations
- [ ] put_access_point_configuration_for_object_lambda
- [ ] put_access_point_policy
- [ ] put_access_point_policy_for_object_lambda
- [ ] put_bucket_lifecycle_configuration
- [ ] put_bucket_policy
- [ ] put_bucket_tagging
- [ ] put_job_tagging
- [ ] put_multi_region_access_point_policy
- [X] put_public_access_block
- [ ] put_storage_lens_configuration
- [ ] put_storage_lens_configuration_tagging
- [ ] update_job_priority
- [ ] update_job_status

