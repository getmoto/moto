.. _implementedservice_cloudfront:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
cloudfront
==========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_cloudfront
            def test_cloudfront_behaviour:
                boto3.client("cloudfront")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] associate_alias
- [ ] create_cache_policy
- [ ] create_cloud_front_origin_access_identity
- [X] create_distribution
  
        This has been tested against an S3-distribution with the
        simplest possible configuration.  Please raise an issue if
        we're not persisting/returning the correct attributes for your
        use-case.
        

- [ ] create_distribution_with_tags
- [ ] create_field_level_encryption_config
- [ ] create_field_level_encryption_profile
- [ ] create_function
- [ ] create_invalidation
- [ ] create_key_group
- [ ] create_monitoring_subscription
- [ ] create_origin_request_policy
- [ ] create_public_key
- [ ] create_realtime_log_config
- [ ] create_response_headers_policy
- [ ] create_streaming_distribution
- [ ] create_streaming_distribution_with_tags
- [ ] delete_cache_policy
- [ ] delete_cloud_front_origin_access_identity
- [X] delete_distribution
  
        The IfMatch-value is ignored - any value is considered valid.
        Calling this function without a value is invalid, per AWS' behaviour
        

- [ ] delete_field_level_encryption_config
- [ ] delete_field_level_encryption_profile
- [ ] delete_function
- [ ] delete_key_group
- [ ] delete_monitoring_subscription
- [ ] delete_origin_request_policy
- [ ] delete_public_key
- [ ] delete_realtime_log_config
- [ ] delete_response_headers_policy
- [ ] delete_streaming_distribution
- [ ] describe_function
- [ ] get_cache_policy
- [ ] get_cache_policy_config
- [ ] get_cloud_front_origin_access_identity
- [ ] get_cloud_front_origin_access_identity_config
- [X] get_distribution
- [ ] get_distribution_config
- [ ] get_field_level_encryption
- [ ] get_field_level_encryption_config
- [ ] get_field_level_encryption_profile
- [ ] get_field_level_encryption_profile_config
- [ ] get_function
- [ ] get_invalidation
- [ ] get_key_group
- [ ] get_key_group_config
- [ ] get_monitoring_subscription
- [ ] get_origin_request_policy
- [ ] get_origin_request_policy_config
- [ ] get_public_key
- [ ] get_public_key_config
- [ ] get_realtime_log_config
- [ ] get_response_headers_policy
- [ ] get_response_headers_policy_config
- [ ] get_streaming_distribution
- [ ] get_streaming_distribution_config
- [ ] list_cache_policies
- [ ] list_cloud_front_origin_access_identities
- [ ] list_conflicting_aliases
- [X] list_distributions
  
        Pagination is not supported yet.
        

- [ ] list_distributions_by_cache_policy_id
- [ ] list_distributions_by_key_group
- [ ] list_distributions_by_origin_request_policy_id
- [ ] list_distributions_by_realtime_log_config
- [ ] list_distributions_by_response_headers_policy_id
- [ ] list_distributions_by_web_acl_id
- [ ] list_field_level_encryption_configs
- [ ] list_field_level_encryption_profiles
- [ ] list_functions
- [ ] list_invalidations
- [ ] list_key_groups
- [ ] list_origin_request_policies
- [ ] list_public_keys
- [ ] list_realtime_log_configs
- [ ] list_response_headers_policies
- [ ] list_streaming_distributions
- [ ] list_tags_for_resource
- [ ] publish_function
- [ ] tag_resource
- [ ] test_function
- [ ] untag_resource
- [ ] update_cache_policy
- [ ] update_cloud_front_origin_access_identity
- [X] update_distribution
  
        The IfMatch-value is ignored - any value is considered valid.
        Calling this function without a value is invalid, per AWS' behaviour
        

- [ ] update_field_level_encryption_config
- [ ] update_field_level_encryption_profile
- [ ] update_function
- [ ] update_key_group
- [ ] update_origin_request_policy
- [ ] update_public_key
- [ ] update_realtime_log_config
- [ ] update_response_headers_policy
- [ ] update_streaming_distribution

