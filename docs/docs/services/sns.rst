.. _implementedservice_sns:

.. |start-h3| raw:: html

    <h3>

.. |end-h3| raw:: html

    </h3>

===
sns
===

.. autoclass:: moto.sns.models.SNSBackend

|start-h3| Implemented features for this service |end-h3|

- [X] add_permission
- [X] check_if_phone_number_is_opted_out
  
        Current implementation returns True for all numbers ending in '99'
        

- [X] confirm_subscription
- [X] create_platform_application
- [X] create_platform_endpoint
- [ ] create_sms_sandbox_phone_number
- [X] create_topic
- [X] delete_endpoint
- [X] delete_platform_application
- [ ] delete_sms_sandbox_phone_number
- [X] delete_topic
- [ ] get_data_protection_policy
- [X] get_endpoint_attributes
- [X] get_platform_application_attributes
- [X] get_sms_attributes
- [ ] get_sms_sandbox_account_status
- [X] get_subscription_attributes
- [X] get_topic_attributes
- [X] list_endpoints_by_platform_application
- [ ] list_origination_numbers
- [X] list_phone_numbers_opted_out
- [X] list_platform_applications
- [ ] list_sms_sandbox_phone_numbers
- [X] list_subscriptions
- [X] list_subscriptions_by_topic
- [X] list_tags_for_resource
- [X] list_topics
- [X] opt_in_phone_number
- [X] publish
- [X] publish_batch
  
        The MessageStructure and MessageDeduplicationId-parameters have not yet been implemented.
        

- [ ] put_data_protection_policy
- [X] remove_permission
- [X] set_endpoint_attributes
- [X] set_platform_application_attributes
- [X] set_sms_attributes
- [X] set_subscription_attributes
- [ ] set_topic_attributes
- [X] subscribe
- [X] tag_resource
- [X] unsubscribe
- [X] untag_resource
- [ ] verify_sms_sandbox_phone_number

