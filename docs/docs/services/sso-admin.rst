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

- [ ] attach_managed_policy_to_permission_set
- [X] create_account_assignment
- [ ] create_instance_access_control_attribute_configuration
- [X] create_permission_set
- [X] delete_account_assignment
- [ ] delete_inline_policy_from_permission_set
- [ ] delete_instance_access_control_attribute_configuration
- [X] delete_permission_set
- [ ] describe_account_assignment_creation_status
- [ ] describe_account_assignment_deletion_status
- [ ] describe_instance_access_control_attribute_configuration
- [X] describe_permission_set
- [ ] describe_permission_set_provisioning_status
- [ ] detach_managed_policy_from_permission_set
- [ ] get_inline_policy_for_permission_set
- [ ] list_account_assignment_creation_status
- [ ] list_account_assignment_deletion_status
- [X] list_account_assignments
  
        Pagination has not yet been implemented
        

- [ ] list_accounts_for_provisioned_permission_set
- [ ] list_instances
- [ ] list_managed_policies_in_permission_set
- [ ] list_permission_set_provisioning_status
- [X] list_permission_sets
- [ ] list_permission_sets_provisioned_to_account
- [ ] list_tags_for_resource
- [ ] provision_permission_set
- [ ] put_inline_policy_to_permission_set
- [ ] tag_resource
- [ ] untag_resource
- [ ] update_instance_access_control_attribute_configuration
- [X] update_permission_set

