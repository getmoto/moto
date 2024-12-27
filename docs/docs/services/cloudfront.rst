.. _implementedservice_cloudfront:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

==========
cloudfront
==========

|start-h3| Implemented features for this service |end-h3|

- [ ] associate_alias
- [ ] copy_distribution
- [ ] create_anycast_ip_list
- [ ] create_cache_policy
- [ ] create_cloud_front_origin_access_identity
- [ ] create_continuous_deployment_policy
- [X] create_distribution
  
        Not all configuration options are supported yet.  Please raise an issue if
        we're not persisting/returning the correct attributes for your
        use-case.
        

- [X] create_distribution_with_tags
- [ ] create_field_level_encryption_config
- [ ] create_field_level_encryption_profile
- [ ] create_function
- [X] create_invalidation
- [X] create_key_group
- [ ] create_key_value_store
- [ ] create_monitoring_subscription
- [X] create_origin_access_control
- [ ] create_origin_request_policy
- [X] create_public_key
- [ ] create_realtime_log_config
- [ ] create_response_headers_policy
- [ ] create_streaming_distribution
- [ ] create_streaming_distribution_with_tags
- [ ] create_vpc_origin
- [ ] delete_anycast_ip_list
- [ ] delete_cache_policy
- [ ] delete_cloud_front_origin_access_identity
- [ ] delete_continuous_deployment_policy
- [X] delete_distribution
  
        The IfMatch-value is ignored - any value is considered valid.
        Calling this function without a value is invalid, per AWS' behaviour
        

- [ ] delete_field_level_encryption_config
- [ ] delete_field_level_encryption_profile
- [ ] delete_function
- [ ] delete_key_group
- [ ] delete_key_value_store
- [ ] delete_monitoring_subscription
- [X] delete_origin_access_control
  
        The IfMatch-parameter is not yet implemented
        

- [ ] delete_origin_request_policy
- [X] delete_public_key
  
        IfMatch is not yet implemented - deletion always succeeds
        

- [ ] delete_realtime_log_config
- [ ] delete_response_headers_policy
- [ ] delete_streaming_distribution
- [ ] delete_vpc_origin
- [ ] describe_function
- [ ] describe_key_value_store
- [ ] get_anycast_ip_list
- [ ] get_cache_policy
- [ ] get_cache_policy_config
- [ ] get_cloud_front_origin_access_identity
- [ ] get_cloud_front_origin_access_identity_config
- [ ] get_continuous_deployment_policy
- [ ] get_continuous_deployment_policy_config
- [X] get_distribution
- [X] get_distribution_config
- [ ] get_field_level_encryption
- [ ] get_field_level_encryption_config
- [ ] get_field_level_encryption_profile
- [ ] get_field_level_encryption_profile_config
- [ ] get_function
- [X] get_invalidation
- [X] get_key_group
- [ ] get_key_group_config
- [ ] get_monitoring_subscription
- [X] get_origin_access_control
- [ ] get_origin_access_control_config
- [ ] get_origin_request_policy
- [ ] get_origin_request_policy_config
- [X] get_public_key
- [ ] get_public_key_config
- [ ] get_realtime_log_config
- [ ] get_response_headers_policy
- [ ] get_response_headers_policy_config
- [ ] get_streaming_distribution
- [ ] get_streaming_distribution_config
- [ ] get_vpc_origin
- [ ] list_anycast_ip_lists
- [ ] list_cache_policies
- [ ] list_cloud_front_origin_access_identities
- [ ] list_conflicting_aliases
- [ ] list_continuous_deployment_policies
- [X] list_distributions
  
        Pagination is not supported yet.
        

- [ ] list_distributions_by_anycast_ip_list_id
- [ ] list_distributions_by_cache_policy_id
- [ ] list_distributions_by_key_group
- [ ] list_distributions_by_origin_request_policy_id
- [ ] list_distributions_by_realtime_log_config
- [ ] list_distributions_by_response_headers_policy_id
- [ ] list_distributions_by_vpc_origin_id
- [ ] list_distributions_by_web_acl_id
- [ ] list_field_level_encryption_configs
- [ ] list_field_level_encryption_profiles
- [ ] list_functions
- [X] list_invalidations
  
        Pagination is not yet implemented
        

- [X] list_key_groups
  
        Pagination is not yet implemented
        

- [ ] list_key_value_stores
- [X] list_origin_access_controls
  
        Pagination is not yet implemented
        

- [ ] list_origin_request_policies
- [X] list_public_keys
  
        Pagination is not yet implemented
        

- [ ] list_realtime_log_configs
- [ ] list_response_headers_policies
- [ ] list_streaming_distributions
- [X] list_tags_for_resource
- [ ] list_vpc_origins
- [ ] publish_function
- [ ] tag_resource
- [ ] test_function
- [ ] untag_resource
- [ ] update_cache_policy
- [ ] update_cloud_front_origin_access_identity
- [ ] update_continuous_deployment_policy
- [X] update_distribution
  
        The IfMatch-value is ignored - any value is considered valid.
        Calling this function without a value is invalid, per AWS' behaviour
        

- [ ] update_distribution_with_staging_config
- [ ] update_field_level_encryption_config
- [ ] update_field_level_encryption_profile
- [ ] update_function
- [ ] update_key_group
- [ ] update_key_value_store
- [X] update_origin_access_control
  
        The IfMatch-parameter is not yet implemented
        

- [ ] update_origin_request_policy
- [ ] update_public_key
- [ ] update_realtime_log_config
- [ ] update_response_headers_policy
- [ ] update_streaming_distribution
- [ ] update_vpc_origin

