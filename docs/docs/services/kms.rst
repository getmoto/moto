.. _implementedservice_kms:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
kms
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_kms
            def test_kms_behaviour:
                boto3.client("kms")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] cancel_key_deletion
- [ ] connect_custom_key_store
- [ ] create_alias
- [ ] create_custom_key_store
- [X] create_grant
- [X] create_key
- [X] decrypt
- [X] delete_alias
  Delete the alias.

- [ ] delete_custom_key_store
- [ ] delete_imported_key_material
- [ ] describe_custom_key_stores
- [X] describe_key
- [X] disable_key
- [X] disable_key_rotation
- [ ] disconnect_custom_key_store
- [X] enable_key
- [X] enable_key_rotation
- [X] encrypt
- [X] generate_data_key
- [ ] generate_data_key_pair
- [ ] generate_data_key_pair_without_plaintext
- [ ] generate_data_key_without_plaintext
- [ ] generate_mac
- [ ] generate_random
- [X] get_key_policy
- [X] get_key_rotation_status
- [ ] get_parameters_for_import
- [ ] get_public_key
- [ ] import_key_material
- [ ] list_aliases
- [X] list_grants
- [ ] list_key_policies
- [X] list_keys
- [X] list_resource_tags
- [X] list_retirable_grants
- [X] put_key_policy
- [X] re_encrypt
- [ ] replicate_key
- [X] retire_grant
- [X] revoke_grant
- [X] schedule_key_deletion
- [ ] sign
- [X] tag_resource
- [X] untag_resource
- [ ] update_alias
- [ ] update_custom_key_store
- [X] update_key_description
- [ ] update_primary_region
- [ ] verify
- [ ] verify_mac

