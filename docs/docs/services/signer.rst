.. _implementedservice_signer:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

======
signer
======

.. autoclass:: moto.signer.models.SignerBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_signer
            def test_signer_behaviour:
                boto3.client("signer")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] add_profile_permission
- [X] cancel_signing_profile
- [ ] describe_signing_job
- [ ] get_revocation_status
- [ ] get_signing_platform
- [X] get_signing_profile
- [ ] list_profile_permissions
- [ ] list_signing_jobs
- [X] list_signing_platforms
  
        Pagination is not yet implemented. The parameters category, partner, target are not yet implemented
        

- [ ] list_signing_profiles
- [ ] list_tags_for_resource
- [X] put_signing_profile
  
        The following parameters are not yet implemented: SigningMaterial, Overrides, SigningParamaters
        

- [ ] remove_profile_permission
- [ ] revoke_signature
- [ ] revoke_signing_profile
- [ ] sign_payload
- [ ] start_signing_job
- [ ] tag_resource
- [ ] untag_resource

