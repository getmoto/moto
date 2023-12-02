.. _implementedservice_sso-admin:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=========
sso-admin
=========

.. autoclass:: moto.ssoadmin.models.SSOAdminBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_ssoadmin
            def test_ssoadmin_behaviour:
                boto3.client("sso-admin")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] attach_customer_managed_policy_reference_to_permission_set
- [ ] attach_managed_policy_to_permission_set
- [X] create_account_assignment
- [ ] create_application
- [ ] create_application_assignment
- [ ] create_instance
- [ ] create_instance_access_control_attribute_configuration
- [X] create_permission_set
- [ ] create_trusted_token_issuer
- [X] delete_account_assignment
- [ ] delete_application
- [ ] delete_application_access_scope
- [ ] delete_application_assignment
- [ ] delete_application_authentication_method
- [ ] delete_application_grant
- [ ] delete_inline_policy_from_permission_set
- [ ] delete_instance
- [ ] delete_instance_access_control_attribute_configuration
- [X] delete_permission_set
- [ ] delete_permissions_boundary_from_permission_set
- [ ] delete_trusted_token_issuer
- [ ] describe_account_assignment_creation_status
- [ ] describe_account_assignment_deletion_status
- [ ] describe_application
- [ ] describe_application_assignment
- [ ] describe_application_provider
- [ ] describe_instance
- [ ] describe_instance_access_control_attribute_configuration
- [X] describe_permission_set
- [ ] describe_permission_set_provisioning_status
- [ ] describe_trusted_token_issuer
- [ ] detach_customer_managed_policy_reference_from_permission_set
- [ ] detach_managed_policy_from_permission_set
- [ ] get_application_access_scope
- [ ] get_application_assignment_configuration
- [ ] get_application_authentication_method
- [ ] get_application_grant
- [ ] get_inline_policy_for_permission_set
- [ ] get_permissions_boundary_for_permission_set
- [ ] list_account_assignment_creation_status
- [ ] list_account_assignment_deletion_status
- [X] list_account_assignments
  
        Pagination has not yet been implemented
        

- [ ] list_account_assignments_for_principal
- [ ] list_accounts_for_provisioned_permission_set
- [ ] list_application_access_scopes
- [ ] list_application_assignments
- [ ] list_application_assignments_for_principal
- [ ] list_application_authentication_methods
- [ ] list_application_grants
- [ ] list_application_providers
- [ ] list_applications
- [ ] list_customer_managed_policy_references_in_permission_set
- [ ] list_instances
- [ ] list_managed_policies_in_permission_set
- [ ] list_permission_set_provisioning_status
- [X] list_permission_sets
- [ ] list_permission_sets_provisioned_to_account
- [ ] list_tags_for_resource
- [ ] list_trusted_token_issuers
- [ ] provision_permission_set
- [ ] put_application_access_scope
- [ ] put_application_assignment_configuration
- [ ] put_application_authentication_method
- [ ] put_application_grant
- [ ] put_inline_policy_to_permission_set
- [ ] put_permissions_boundary_to_permission_set
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_application
- [ ] update_instance
- [ ] update_instance_access_control_attribute_configuration
- [X] update_permission_set
- [ ] update_trusted_token_issuer

