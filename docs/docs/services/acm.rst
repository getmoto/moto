.. _implementedservice_acm:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
acm
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_acm
            def test_acm_behaviour:
                boto3.client("acm")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] add_tags_to_certificate
- [X] delete_certificate
- [ ] describe_certificate
- [X] export_certificate
- [ ] get_account_configuration
- [X] get_certificate
- [ ] import_certificate
- [ ] list_certificates
- [ ] list_tags_for_certificate
- [ ] put_account_configuration
- [X] remove_tags_from_certificate
- [ ] renew_certificate
- [X] request_certificate
  
        The parameter DomainValidationOptions has not yet been implemented
        

- [ ] resend_validation_email
- [ ] update_certificate_options

