.. _implementedservice_pinpoint:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

========
pinpoint
========

.. autoclass:: moto.pinpoint.models.PinpointBackend

|start-h3| Example usage |end-h3|

.. sourcecode:: python

            @mock_pinpoint
            def test_pinpoint_behaviour:
                boto3.client("pinpoint")
                ...



|start-h3| Implemented features for this service |end-h3|

- [X] create_app
- [ ] create_campaign
- [ ] create_email_template
- [ ] create_export_job
- [ ] create_import_job
- [ ] create_in_app_template
- [ ] create_journey
- [ ] create_push_template
- [ ] create_recommender_configuration
- [ ] create_segment
- [ ] create_sms_template
- [ ] create_voice_template
- [ ] delete_adm_channel
- [ ] delete_apns_channel
- [ ] delete_apns_sandbox_channel
- [ ] delete_apns_voip_channel
- [ ] delete_apns_voip_sandbox_channel
- [X] delete_app
- [ ] delete_baidu_channel
- [ ] delete_campaign
- [ ] delete_email_channel
- [ ] delete_email_template
- [ ] delete_endpoint
- [X] delete_event_stream
- [ ] delete_gcm_channel
- [ ] delete_in_app_template
- [ ] delete_journey
- [ ] delete_push_template
- [ ] delete_recommender_configuration
- [ ] delete_segment
- [ ] delete_sms_channel
- [ ] delete_sms_template
- [ ] delete_user_endpoints
- [ ] delete_voice_channel
- [ ] delete_voice_template
- [ ] get_adm_channel
- [ ] get_apns_channel
- [ ] get_apns_sandbox_channel
- [ ] get_apns_voip_channel
- [ ] get_apns_voip_sandbox_channel
- [X] get_app
- [ ] get_application_date_range_kpi
- [X] get_application_settings
- [X] get_apps
  
        Pagination is not yet implemented
        

- [ ] get_baidu_channel
- [ ] get_campaign
- [ ] get_campaign_activities
- [ ] get_campaign_date_range_kpi
- [ ] get_campaign_version
- [ ] get_campaign_versions
- [ ] get_campaigns
- [ ] get_channels
- [ ] get_email_channel
- [ ] get_email_template
- [ ] get_endpoint
- [X] get_event_stream
- [ ] get_export_job
- [ ] get_export_jobs
- [ ] get_gcm_channel
- [ ] get_import_job
- [ ] get_import_jobs
- [ ] get_in_app_messages
- [ ] get_in_app_template
- [ ] get_journey
- [ ] get_journey_date_range_kpi
- [ ] get_journey_execution_activity_metrics
- [ ] get_journey_execution_metrics
- [ ] get_push_template
- [ ] get_recommender_configuration
- [ ] get_recommender_configurations
- [ ] get_segment
- [ ] get_segment_export_jobs
- [ ] get_segment_import_jobs
- [ ] get_segment_version
- [ ] get_segment_versions
- [ ] get_segments
- [ ] get_sms_channel
- [ ] get_sms_template
- [ ] get_user_endpoints
- [ ] get_voice_channel
- [ ] get_voice_template
- [ ] list_journeys
- [X] list_tags_for_resource
- [ ] list_template_versions
- [ ] list_templates
- [ ] phone_number_validate
- [X] put_event_stream
- [ ] put_events
- [ ] remove_attributes
- [ ] send_messages
- [ ] send_otp_message
- [ ] send_users_messages
- [X] tag_resource
- [X] untag_resource
- [ ] update_adm_channel
- [ ] update_apns_channel
- [ ] update_apns_sandbox_channel
- [ ] update_apns_voip_channel
- [ ] update_apns_voip_sandbox_channel
- [X] update_application_settings
- [ ] update_baidu_channel
- [ ] update_campaign
- [ ] update_email_channel
- [ ] update_email_template
- [ ] update_endpoint
- [ ] update_endpoints_batch
- [ ] update_gcm_channel
- [ ] update_in_app_template
- [ ] update_journey
- [ ] update_journey_state
- [ ] update_push_template
- [ ] update_recommender_configuration
- [ ] update_segment
- [ ] update_sms_channel
- [ ] update_sms_template
- [ ] update_template_active_version
- [ ] update_voice_channel
- [ ] update_voice_template
- [ ] verify_otp_message

