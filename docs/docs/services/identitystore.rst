.. _implementedservice_identitystore:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=============
identitystore
=============

.. autoclass:: moto.identitystore.models.IdentityStoreBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_identitystore
            def test_identitystore_behaviour:
                boto3.client("identitystore")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_group
- [ ] create_group_membership
- [ ] create_user
- [ ] delete_group
- [ ] delete_group_membership
- [ ] delete_user
- [ ] describe_group
- [ ] describe_group_membership
- [ ] describe_user
- [ ] get_group_id
- [ ] get_group_membership_id
- [ ] get_user_id
- [ ] is_member_in_groups
- [ ] list_group_memberships
- [ ] list_group_memberships_for_member
- [ ] list_groups
- [ ] list_users
- [ ] update_group
- [ ] update_user

