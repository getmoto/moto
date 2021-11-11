.. _implementedservice_ram:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
ram
===



|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_ram
            def test_ram_behaviour:
                boto3.client("ram")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] accept_resource_share_invitation
- [ ] associate_resource_share
- [ ] associate_resource_share_permission
- [X] create_resource_share
- [X] delete_resource_share
- [ ] disassociate_resource_share
- [ ] disassociate_resource_share_permission
- [X] enable_sharing_with_aws_organization
- [ ] get_permission
- [ ] get_resource_policies
- [ ] get_resource_share_associations
- [ ] get_resource_share_invitations
- [X] get_resource_shares
- [ ] list_pending_invitation_resources
- [ ] list_permissions
- [ ] list_principals
- [ ] list_resource_share_permissions
- [ ] list_resource_types
- [ ] list_resources
- [ ] promote_resource_share_created_from_policy
- [ ] reject_resource_share_invitation
- [ ] tag_resource
- [ ] untag_resource
- [X] update_resource_share

