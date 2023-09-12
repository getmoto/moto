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
- [X] create_group_membership
- [X] create_user
- [X] delete_group
- [X] delete_group_membership
- [X] delete_user
- [ ] describe_group
- [ ] describe_group_membership
- [X] describe_user
- [X] get_group_id
- [ ] get_group_membership_id
- [ ] get_user_id
- [ ] is_member_in_groups
- [X] list_group_memberships
- [ ] list_group_memberships_for_member
- [X] list_groups
- [X] list_users
- [ ] update_group
- [ ] update_user

