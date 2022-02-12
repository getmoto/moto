.. _implementedservice_glacier:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=======
glacier
=======

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_glacier
            def test_glacier_behaviour:
                boto3.client("glacier")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] abort_multipart_upload
- [ ] abort_vault_lock
- [ ] add_tags_to_vault
- [ ] complete_multipart_upload
- [ ] complete_vault_lock
- [X] create_vault
- [ ] delete_archive
- [X] delete_vault
- [ ] delete_vault_access_policy
- [ ] delete_vault_notifications
- [X] describe_job
- [ ] describe_vault
- [ ] get_data_retrieval_policy
- [X] get_job_output
- [ ] get_vault_access_policy
- [ ] get_vault_lock
- [ ] get_vault_notifications
- [X] initiate_job
- [ ] initiate_multipart_upload
- [ ] initiate_vault_lock
- [X] list_jobs
- [ ] list_multipart_uploads
- [ ] list_parts
- [ ] list_provisioned_capacity
- [ ] list_tags_for_vault
- [X] list_vaults
- [ ] purchase_provisioned_capacity
- [ ] remove_tags_from_vault
- [ ] set_data_retrieval_policy
- [ ] set_vault_access_policy
- [ ] set_vault_notifications
- [X] upload_archive
- [ ] upload_multipart_part

