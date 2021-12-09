.. _implementedservice_cognito-identity:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

================
cognito-identity
================

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_cognitoidentity
            def test_cognito-identity_behaviour:
                boto3.client("cognito-identity")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_identity_pool
- [ ] delete_identities
- [ ] delete_identity_pool
- [ ] describe_identity
- [X] describe_identity_pool
- [X] get_credentials_for_identity
- [X] get_id
- [ ] get_identity_pool_roles
- [X] get_open_id_token
- [X] get_open_id_token_for_developer_identity
- [ ] get_principal_tag_attribute_map
- [X] list_identities
- [ ] list_identity_pools
- [ ] list_tags_for_resource
- [ ] lookup_developer_identity
- [ ] merge_developer_identities
- [ ] set_identity_pool_roles
- [ ] set_principal_tag_attribute_map
- [ ] tag_resource
- [ ] unlink_developer_identity
- [ ] unlink_identity
- [ ] untag_resource
- [X] update_identity_pool

