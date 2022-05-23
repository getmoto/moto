.. _implementedservice_cognito-idp:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===========
cognito-idp
===========

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_cognitoidp
            def test_cognitoidp_behaviour:
                boto3.client("cognito-idp")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] add_custom_attributes
- [X] admin_add_user_to_group
- [X] admin_confirm_sign_up
- [X] admin_create_user
- [X] admin_delete_user
- [X] admin_delete_user_attributes
- [ ] admin_disable_provider_for_user
- [X] admin_disable_user
- [X] admin_enable_user
- [ ] admin_forget_device
- [ ] admin_get_device
- [X] admin_get_user
- [X] admin_initiate_auth
- [ ] admin_link_provider_for_user
- [ ] admin_list_devices
- [X] admin_list_groups_for_user
- [ ] admin_list_user_auth_events
- [X] admin_remove_user_from_group
- [X] admin_reset_user_password
- [ ] admin_respond_to_auth_challenge
- [X] admin_set_user_mfa_preference
- [X] admin_set_user_password
- [ ] admin_set_user_settings
- [ ] admin_update_auth_event_feedback
- [ ] admin_update_device_status
- [X] admin_update_user_attributes
- [X] admin_user_global_sign_out
- [X] associate_software_token
- [X] change_password
- [ ] confirm_device
- [X] confirm_forgot_password
- [X] confirm_sign_up
- [X] create_group
- [X] create_identity_provider
- [X] create_resource_server
- [ ] create_user_import_job
- [X] create_user_pool
- [X] create_user_pool_client
- [X] create_user_pool_domain
- [X] delete_group
- [X] delete_identity_provider
- [ ] delete_resource_server
- [ ] delete_user
- [ ] delete_user_attributes
- [X] delete_user_pool
- [X] delete_user_pool_client
- [X] delete_user_pool_domain
- [X] describe_identity_provider
- [ ] describe_resource_server
- [ ] describe_risk_configuration
- [ ] describe_user_import_job
- [X] describe_user_pool
- [X] describe_user_pool_client
- [X] describe_user_pool_domain
- [ ] forget_device
- [X] forgot_password
  
        The ForgotPassword operation is partially broken in AWS. If the input is 100% correct it works fine.

        Otherwise you get semi-random garbage and HTTP 200 OK, for example:
        - recovery for username which is not registered in any cognito pool
        - recovery for username belonging to a different user pool than the client id is registered to
        - phone-based recovery for a user without phone_number / phone_number_verified attributes
        - same as above, but email / email_verified
        

- [ ] get_csv_header
- [ ] get_device
- [X] get_group
- [ ] get_identity_provider_by_identifier
- [ ] get_signing_certificate
- [ ] get_ui_customization
- [X] get_user
- [ ] get_user_attribute_verification_code
- [X] get_user_pool_mfa_config
- [X] global_sign_out
- [X] initiate_auth
- [ ] list_devices
- [X] list_groups
- [X] list_identity_providers
- [ ] list_resource_servers
- [ ] list_tags_for_resource
- [ ] list_user_import_jobs
- [X] list_user_pool_clients
- [X] list_user_pools
- [X] list_users
- [X] list_users_in_group
- [ ] resend_confirmation_code
- [X] respond_to_auth_challenge
- [ ] revoke_token
- [ ] set_risk_configuration
- [ ] set_ui_customization
- [X] set_user_mfa_preference
- [X] set_user_pool_mfa_config
- [ ] set_user_settings
- [X] sign_up
- [ ] start_user_import_job
- [ ] stop_user_import_job
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_auth_event_feedback
- [ ] update_device_status
- [X] update_group
- [X] update_identity_provider
- [ ] update_resource_server
- [X] update_user_attributes
  
        The parameter ClientMetadata has not yet been implemented. No CodeDeliveryDetails are returned.
        

- [X] update_user_pool
- [X] update_user_pool_client
- [X] update_user_pool_domain
- [X] verify_software_token
  
        The parameter UserCode has not yet been implemented
        

- [ ] verify_user_attribute

