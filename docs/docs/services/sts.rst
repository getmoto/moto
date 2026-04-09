.. _implementedservice_sts:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
sts
===

|start-h3| Implemented features for this service |end-h3|

- [X] assume_role
  
        Assume an IAM Role. Note that the role does not need to exist. The ARN can point to another account, providing an opportunity to switch accounts.
        

- [X] assume_role_with_saml
- [X] assume_role_with_web_identity
- [ ] assume_root
- [ ] decode_authorization_message
- [X] get_access_key_info
  Return the account ID associated with the given access key.

        In real AWS, this looks up the owning account. In moto, we check
        IAM users/access keys across known accounts; if nothing matches,
        we return the current account.
        

- [X] get_caller_identity
- [ ] get_delegated_access_token
- [X] get_federation_token
- [X] get_session_token
- [ ] get_web_identity_token

