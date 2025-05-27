.. _implementedservice_acm-pca:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=======
acm-pca
=======

.. autoclass:: moto.acmpca.models.ACMPCABackend

|start-h3| Implemented features for this service |end-h3|

- [X] create_certificate_authority
  
        The following parameters are not yet implemented: IdempotencyToken, KeyStorageSecurityStandard, UsageMode
        

- [ ] create_certificate_authority_audit_report
- [ ] create_permission
- [X] delete_certificate_authority
- [ ] delete_permission
- [X] delete_policy
  
        Deletes the resource-based policy attached to a private CA.
        

- [X] describe_certificate_authority
- [ ] describe_certificate_authority_audit_report
- [X] get_certificate
  
        The CertificateChain will always return None for now
        

- [X] get_certificate_authority_certificate
- [X] get_certificate_authority_csr
- [X] get_policy
  
        Retrieves the resource-based policy attached to a private CA.
        

- [X] import_certificate_authority_certificate
- [X] issue_certificate
  
        The following parameters are not yet implemented: ApiPassthrough, SigningAlgorithm, Validity, ValidityNotBefore, IdempotencyToken
        Some fields of the resulting certificate will have default values, instead of using the CSR
        

- [X] list_certificate_authorities
  
        Lists the private certificate authorities that you created by using the CreateCertificateAuthority action.
        

- [ ] list_permissions
- [X] list_tags
  
        Pagination is not yet implemented
        

- [X] put_policy
  
        Attaches a resource-based policy to a private CA.
        

- [ ] restore_certificate_authority
- [X] revoke_certificate
  
        This is currently a NO-OP
        

- [X] tag_certificate_authority
- [X] untag_certificate_authority
- [X] update_certificate_authority

