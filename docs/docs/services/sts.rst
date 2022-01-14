.. _implementedservice_sts:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
sts
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_sts
            def test_sts_behaviour:
                boto3.client("sts")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] assume_role
- [X] assume_role_with_saml
- [X] assume_role_with_web_identity
- [ ] decode_authorization_message
- [ ] get_access_key_info
- [X] get_caller_identity
- [X] get_federation_token
- [X] get_session_token

