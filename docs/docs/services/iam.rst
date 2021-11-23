.. _implementedservice_iam:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
iam
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_iam
            def test_iam_behaviour:
                boto3.client("iam")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_client_id_to_open_id_connect_provider
- [X] add_role_to_instance_profile
- [X] add_user_to_group
- [X] attach_group_policy
- [X] attach_role_policy
- [X] attach_user_policy
- [ ] change_password
- [X] create_access_key
- [X] create_account_alias
- [X] create_group
- [X] create_instance_profile
- [X] create_login_profile
- [X] create_open_id_connect_provider
- [X] create_policy
- [X] create_policy_version
- [X] create_role
- [X] create_saml_provider
- [ ] create_service_linked_role
- [ ] create_service_specific_credential
- [X] create_user
- [X] create_virtual_mfa_device
- [X] deactivate_mfa_device
  Deactivate and detach MFA Device from user if device exists.

- [X] delete_access_key
- [X] delete_account_alias
- [X] delete_account_password_policy
- [X] delete_group
- [X] delete_group_policy
- [X] delete_instance_profile
- [X] delete_login_profile
- [X] delete_open_id_connect_provider
- [X] delete_policy
- [X] delete_policy_version
- [X] delete_role
- [X] delete_role_permissions_boundary
- [X] delete_role_policy
- [X] delete_saml_provider
- [X] delete_server_certificate
- [ ] delete_service_linked_role
- [ ] delete_service_specific_credential
- [X] delete_signing_certificate
- [X] delete_ssh_public_key
- [X] delete_user
- [ ] delete_user_permissions_boundary
- [X] delete_user_policy
- [X] delete_virtual_mfa_device
- [X] detach_group_policy
- [X] detach_role_policy
- [X] detach_user_policy
- [X] enable_mfa_device
  Enable MFA Device for user.

- [ ] generate_credential_report
- [ ] generate_organizations_access_report
- [ ] generate_service_last_accessed_details
- [X] get_access_key_last_used
- [X] get_account_authorization_details
- [X] get_account_password_policy
- [X] get_account_summary
- [ ] get_context_keys_for_custom_policy
- [ ] get_context_keys_for_principal_policy
- [X] get_credential_report
- [X] get_group
- [X] get_group_policy
- [X] get_instance_profile
- [X] get_login_profile
- [X] get_open_id_connect_provider
- [ ] get_organizations_access_report
- [X] get_policy
- [X] get_policy_version
- [X] get_role
- [X] get_role_policy
- [X] get_saml_provider
- [X] get_server_certificate
- [ ] get_service_last_accessed_details
- [ ] get_service_last_accessed_details_with_entities
- [ ] get_service_linked_role_deletion_status
- [X] get_ssh_public_key
- [X] get_user
- [X] get_user_policy
- [ ] list_access_keys
- [X] list_account_aliases
- [X] list_attached_group_policies
- [X] list_attached_role_policies
- [X] list_attached_user_policies
- [ ] list_entities_for_policy
- [X] list_group_policies
- [X] list_groups
- [ ] list_groups_for_user
- [ ] list_instance_profile_tags
- [ ] list_instance_profiles
- [ ] list_instance_profiles_for_role
- [ ] list_mfa_device_tags
- [X] list_mfa_devices
- [ ] list_open_id_connect_provider_tags
- [X] list_open_id_connect_providers
- [X] list_policies
- [ ] list_policies_granting_service_access
- [X] list_policy_tags
- [X] list_policy_versions
- [X] list_role_policies
- [X] list_role_tags
- [X] list_roles
- [ ] list_saml_provider_tags
- [X] list_saml_providers
- [ ] list_server_certificate_tags
- [ ] list_server_certificates
- [ ] list_service_specific_credentials
- [X] list_signing_certificates
- [ ] list_ssh_public_keys
- [X] list_user_policies
- [X] list_user_tags
- [X] list_users
- [X] list_virtual_mfa_devices
- [X] put_group_policy
- [X] put_role_permissions_boundary
- [X] put_role_policy
- [ ] put_user_permissions_boundary
- [X] put_user_policy
- [ ] remove_client_id_from_open_id_connect_provider
- [X] remove_role_from_instance_profile
- [X] remove_user_from_group
- [ ] reset_service_specific_credential
- [ ] resync_mfa_device
- [X] set_default_policy_version
- [ ] set_security_token_service_preferences
- [ ] simulate_custom_policy
- [ ] simulate_principal_policy
- [ ] tag_instance_profile
- [ ] tag_mfa_device
- [ ] tag_open_id_connect_provider
- [X] tag_policy
- [X] tag_role
- [ ] tag_saml_provider
- [ ] tag_server_certificate
- [X] tag_user
- [ ] untag_instance_profile
- [ ] untag_mfa_device
- [ ] untag_open_id_connect_provider
- [X] untag_policy
- [X] untag_role
- [ ] untag_saml_provider
- [ ] untag_server_certificate
- [X] untag_user
- [X] update_access_key
- [X] update_account_password_policy
- [ ] update_assume_role_policy
- [ ] update_group
- [X] update_login_profile
- [ ] update_open_id_connect_provider_thumbprint
- [X] update_role
- [X] update_role_description
- [X] update_saml_provider
- [ ] update_server_certificate
- [ ] update_service_specific_credential
- [X] update_signing_certificate
- [X] update_ssh_public_key
- [X] update_user
- [X] upload_server_certificate
- [X] upload_signing_certificate
- [X] upload_ssh_public_key

