.. _implementedservice_ses:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
ses
===

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_ses
            def test_ses_behaviour:
                boto3.client("ses")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] clone_receipt_rule_set
- [X] create_configuration_set
- [X] create_configuration_set_event_destination
- [ ] create_configuration_set_tracking_options
- [ ] create_custom_verification_email_template
- [ ] create_receipt_filter
- [X] create_receipt_rule
- [X] create_receipt_rule_set
- [ ] create_template
- [ ] delete_configuration_set
- [ ] delete_configuration_set_event_destination
- [ ] delete_configuration_set_tracking_options
- [ ] delete_custom_verification_email_template
- [X] delete_identity
- [ ] delete_identity_policy
- [ ] delete_receipt_filter
- [ ] delete_receipt_rule
- [ ] delete_receipt_rule_set
- [ ] delete_template
- [ ] delete_verified_email_address
- [ ] describe_active_receipt_rule_set
- [ ] describe_configuration_set
- [X] describe_receipt_rule
- [X] describe_receipt_rule_set
- [ ] get_account_sending_enabled
- [ ] get_custom_verification_email_template
- [ ] get_identity_dkim_attributes
- [ ] get_identity_mail_from_domain_attributes
- [X] get_identity_notification_attributes
- [ ] get_identity_policies
- [ ] get_identity_verification_attributes
- [X] get_send_quota
- [X] get_send_statistics
- [X] get_template
- [ ] list_configuration_sets
- [ ] list_custom_verification_email_templates
- [X] list_identities
- [ ] list_identity_policies
- [ ] list_receipt_filters
- [ ] list_receipt_rule_sets
- [X] list_templates
- [X] list_verified_email_addresses
- [ ] put_configuration_set_delivery_options
- [ ] put_identity_policy
- [ ] reorder_receipt_rule_set
- [ ] send_bounce
- [ ] send_bulk_templated_email
- [ ] send_custom_verification_email
- [X] send_email
- [X] send_raw_email
- [X] send_templated_email
- [ ] set_active_receipt_rule_set
- [ ] set_identity_dkim_enabled
- [X] set_identity_feedback_forwarding_enabled
- [ ] set_identity_headers_in_notifications_enabled
- [ ] set_identity_mail_from_domain
- [X] set_identity_notification_topic
- [ ] set_receipt_rule_position
- [ ] test_render_template
- [ ] update_account_sending_enabled
- [ ] update_configuration_set_event_destination
- [ ] update_configuration_set_reputation_metrics_enabled
- [ ] update_configuration_set_sending_enabled
- [ ] update_configuration_set_tracking_options
- [ ] update_custom_verification_email_template
- [X] update_receipt_rule
- [X] update_template
- [ ] verify_domain_dkim
- [ ] verify_domain_identity
- [X] verify_email_address
- [X] verify_email_identity

