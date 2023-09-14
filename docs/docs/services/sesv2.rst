.. _implementedservice_sesv2:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

=====
sesv2
=====

.. autoclass:: moto.sesv2.models.SESV2Backend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_sesv2
            def test_sesv2_behaviour:
                boto3.client("sesv2")
                ...



|start-h3| Implemented features for this service |end-h3|

- [ ] batch_get_metric_data
- [ ] cancel_export_job
- [ ] create_configuration_set
- [ ] create_configuration_set_event_destination
- [X] create_contact
- [X] create_contact_list
- [ ] create_custom_verification_email_template
- [ ] create_dedicated_ip_pool
- [ ] create_deliverability_test_report
- [ ] create_email_identity
- [ ] create_email_identity_policy
- [ ] create_email_template
- [ ] create_export_job
- [ ] create_import_job
- [ ] delete_configuration_set
- [ ] delete_configuration_set_event_destination
- [X] delete_contact
- [X] delete_contact_list
- [ ] delete_custom_verification_email_template
- [ ] delete_dedicated_ip_pool
- [ ] delete_email_identity
- [ ] delete_email_identity_policy
- [ ] delete_email_template
- [ ] delete_suppressed_destination
- [ ] get_account
- [ ] get_blacklist_reports
- [ ] get_configuration_set
- [ ] get_configuration_set_event_destinations
- [X] get_contact
- [X] get_contact_list
- [ ] get_custom_verification_email_template
- [ ] get_dedicated_ip
- [ ] get_dedicated_ip_pool
- [ ] get_dedicated_ips
- [ ] get_deliverability_dashboard_options
- [ ] get_deliverability_test_report
- [ ] get_domain_deliverability_campaign
- [ ] get_domain_statistics_report
- [ ] get_email_identity
- [ ] get_email_identity_policies
- [ ] get_email_template
- [ ] get_export_job
- [ ] get_import_job
- [ ] get_message_insights
- [ ] get_suppressed_destination
- [ ] list_configuration_sets
- [X] list_contact_lists
- [X] list_contacts
- [ ] list_custom_verification_email_templates
- [ ] list_dedicated_ip_pools
- [ ] list_deliverability_test_reports
- [ ] list_domain_deliverability_campaigns
- [ ] list_email_identities
- [ ] list_email_templates
- [ ] list_export_jobs
- [ ] list_import_jobs
- [ ] list_recommendations
- [ ] list_suppressed_destinations
- [ ] list_tags_for_resource
- [ ] put_account_dedicated_ip_warmup_attributes
- [ ] put_account_details
- [ ] put_account_sending_attributes
- [ ] put_account_suppression_attributes
- [ ] put_account_vdm_attributes
- [ ] put_configuration_set_delivery_options
- [ ] put_configuration_set_reputation_options
- [ ] put_configuration_set_sending_options
- [ ] put_configuration_set_suppression_options
- [ ] put_configuration_set_tracking_options
- [ ] put_configuration_set_vdm_options
- [ ] put_dedicated_ip_in_pool
- [ ] put_dedicated_ip_pool_scaling_attributes
- [ ] put_dedicated_ip_warmup_attributes
- [ ] put_deliverability_dashboard_option
- [ ] put_email_identity_configuration_set_attributes
- [ ] put_email_identity_dkim_attributes
- [ ] put_email_identity_dkim_signing_attributes
- [ ] put_email_identity_feedback_attributes
- [ ] put_email_identity_mail_from_attributes
- [ ] put_suppressed_destination
- [ ] send_bulk_email
- [ ] send_custom_verification_email
- [X] send_email
- [ ] tag_resource
- [ ] test_render_email_template
- [ ] untag_resource
- [ ] update_configuration_set_event_destination
- [ ] update_contact
- [ ] update_contact_list
- [ ] update_custom_verification_email_template
- [ ] update_email_identity_policy
- [ ] update_email_template

