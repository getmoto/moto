import base64

from moto.core.responses import BaseResponse
from .models import ses_backend
from datetime import datetime


class EmailResponse(BaseResponse):
    def verify_email_identity(self):
        address = self.querystring.get("EmailAddress")[0]
        ses_backend.verify_email_identity(address)
        template = self.response_template(VERIFY_EMAIL_IDENTITY)
        return template.render()

    def verify_email_address(self):
        address = self.querystring.get("EmailAddress")[0]
        ses_backend.verify_email_address(address)
        template = self.response_template(VERIFY_EMAIL_ADDRESS)
        return template.render()

    def list_identities(self):
        identities = ses_backend.list_identities()
        template = self.response_template(LIST_IDENTITIES_RESPONSE)
        return template.render(identities=identities)

    def list_verified_email_addresses(self):
        email_addresses = ses_backend.list_verified_email_addresses()
        template = self.response_template(LIST_VERIFIED_EMAIL_RESPONSE)
        return template.render(email_addresses=email_addresses)

    def verify_domain_dkim(self):
        domain = self.querystring.get("Domain")[0]
        ses_backend.verify_domain(domain)
        template = self.response_template(VERIFY_DOMAIN_DKIM_RESPONSE)
        return template.render()

    def verify_domain_identity(self):
        domain = self.querystring.get("Domain")[0]
        ses_backend.verify_domain(domain)
        template = self.response_template(VERIFY_DOMAIN_IDENTITY_RESPONSE)
        return template.render()

    def delete_identity(self):
        domain = self.querystring.get("Identity")[0]
        ses_backend.delete_identity(domain)
        template = self.response_template(DELETE_IDENTITY_RESPONSE)
        return template.render()

    def send_email(self):
        bodydatakey = "Message.Body.Text.Data"
        if "Message.Body.Html.Data" in self.querystring:
            bodydatakey = "Message.Body.Html.Data"
        body = self.querystring.get(bodydatakey)[0]
        source = self.querystring.get("Source")[0]
        subject = self.querystring.get("Message.Subject.Data")[0]
        destinations = {"ToAddresses": [], "CcAddresses": [], "BccAddresses": []}
        for dest_type in destinations:
            # consume up to 51 to allow exception
            for i in range(1, 52):
                field = "Destination.%s.member.%s" % (dest_type, i)
                address = self.querystring.get(field)
                if address is None:
                    break
                destinations[dest_type].append(address[0])

        message = ses_backend.send_email(
            source, subject, body, destinations, self.region
        )
        template = self.response_template(SEND_EMAIL_RESPONSE)
        return template.render(message=message)

    def send_templated_email(self):
        source = self.querystring.get("Source")[0]
        template = self.querystring.get("Template")
        template_data = self.querystring.get("TemplateData")

        destinations = {"ToAddresses": [], "CcAddresses": [], "BccAddresses": []}
        for dest_type in destinations:
            # consume up to 51 to allow exception
            for i in range(1, 52):
                field = "Destination.%s.member.%s" % (dest_type, i)
                address = self.querystring.get(field)
                if address is None:
                    break
                destinations[dest_type].append(address[0])

        message = ses_backend.send_templated_email(
            source, template, template_data, destinations, self.region
        )
        template = self.response_template(SEND_TEMPLATED_EMAIL_RESPONSE)
        return template.render(message=message)

    def send_raw_email(self):
        source = self.querystring.get("Source")
        if source is not None:
            (source,) = source

        raw_data = self.querystring.get("RawMessage.Data")[0]
        raw_data = base64.b64decode(raw_data)
        raw_data = raw_data.decode("utf-8")
        destinations = []
        # consume up to 51 to allow exception
        for i in range(1, 52):
            field = "Destinations.member.%s" % i
            address = self.querystring.get(field)
            if address is None:
                break
            destinations.append(address[0])

        message = ses_backend.send_raw_email(
            source, destinations, raw_data, self.region
        )
        template = self.response_template(SEND_RAW_EMAIL_RESPONSE)
        return template.render(message=message)

    def get_send_quota(self):
        quota = ses_backend.get_send_quota()
        template = self.response_template(GET_SEND_QUOTA_RESPONSE)
        return template.render(quota=quota)

    def get_identity_notification_attributes(self):
        identities = self._get_params()["Identities"]
        identities = ses_backend.get_identity_notification_attributes(identities)
        template = self.response_template(GET_IDENTITY_NOTIFICATION_ATTRIBUTES)
        return template.render(identities=identities)

    def set_identity_feedback_forwarding_enabled(self):
        identity = self._get_param("Identity")
        enabled = self._get_bool_param("ForwardingEnabled")
        ses_backend.set_identity_feedback_forwarding_enabled(identity, enabled)
        template = self.response_template(SET_IDENTITY_FORWARDING_ENABLED_RESPONSE)
        return template.render()

    def set_identity_notification_topic(self):

        identity = self.querystring.get("Identity")[0]
        not_type = self.querystring.get("NotificationType")[0]
        sns_topic = self.querystring.get("SnsTopic")
        if sns_topic:
            sns_topic = sns_topic[0]

        ses_backend.set_identity_notification_topic(identity, not_type, sns_topic)
        template = self.response_template(SET_IDENTITY_NOTIFICATION_TOPIC_RESPONSE)
        return template.render()

    def get_send_statistics(self):
        statistics = ses_backend.get_send_statistics()
        template = self.response_template(GET_SEND_STATISTICS)
        return template.render(all_statistics=[statistics])

    def create_configuration_set(self):
        configuration_set_name = self.querystring.get("ConfigurationSet.Name")[0]
        ses_backend.create_configuration_set(
            configuration_set_name=configuration_set_name
        )
        template = self.response_template(CREATE_CONFIGURATION_SET)
        return template.render()

    def create_configuration_set_event_destination(self):

        configuration_set_name = self._get_param("ConfigurationSetName")
        is_configuration_event_enabled = self.querystring.get(
            "EventDestination.Enabled"
        )[0]
        configuration_event_name = self.querystring.get("EventDestination.Name")[0]
        event_topic_arn = self.querystring.get(
            "EventDestination.SNSDestination.TopicARN"
        )[0]
        event_matching_types = self._get_multi_param(
            "EventDestination.MatchingEventTypes.member"
        )

        event_destination = {
            "Name": configuration_event_name,
            "Enabled": is_configuration_event_enabled,
            "EventMatchingTypes": event_matching_types,
            "SNSDestination": event_topic_arn,
        }

        ses_backend.create_configuration_set_event_destination(
            configuration_set_name=configuration_set_name,
            event_destination=event_destination,
        )

        template = self.response_template(CREATE_CONFIGURATION_SET_EVENT_DESTINATION)
        return template.render()

    def create_template(self):
        template_data = self._get_dict_param("Template")
        template_info = {}
        template_info["text_part"] = template_data.get("._text_part", "")
        template_info["html_part"] = template_data.get("._html_part", "")
        template_info["template_name"] = template_data.get("._name", "")
        template_info["subject_part"] = template_data.get("._subject_part", "")
        template_info["Timestamp"] = datetime.utcnow()
        ses_backend.add_template(template_info=template_info)
        template = self.response_template(CREATE_TEMPLATE)
        return template.render()

    def update_template(self):
        template_data = self._get_dict_param("Template")
        template_info = {}
        template_info["text_part"] = template_data.get("._text_part", "")
        template_info["html_part"] = template_data.get("._html_part", "")
        template_info["template_name"] = template_data.get("._name", "")
        template_info["subject_part"] = template_data.get("._subject_part", "")
        template_info["Timestamp"] = datetime.utcnow()
        ses_backend.update_template(template_info=template_info)
        template = self.response_template(UPDATE_TEMPLATE)
        return template.render()

    def get_template(self):
        template_name = self._get_param("TemplateName")
        template_data = ses_backend.get_template(template_name)
        template = self.response_template(GET_TEMPLATE)
        return template.render(template_data=template_data)

    def list_templates(self):
        email_templates = ses_backend.list_templates()
        template = self.response_template(LIST_TEMPLATES)
        return template.render(templates=email_templates)

    def test_render_template(self):
        render_info = self._get_dict_param("Template")
        rendered_template = ses_backend.render_template(render_info)
        template = self.response_template(RENDER_TEMPLATE)
        return template.render(template=rendered_template)

    def create_receipt_rule_set(self):
        rule_set_name = self._get_param("RuleSetName")
        ses_backend.create_receipt_rule_set(rule_set_name)
        template = self.response_template(CREATE_RECEIPT_RULE_SET)
        return template.render()

    def create_receipt_rule(self):
        rule_set_name = self._get_param("RuleSetName")
        rule = self._get_dict_param("Rule.")
        ses_backend.create_receipt_rule(rule_set_name, rule)
        template = self.response_template(CREATE_RECEIPT_RULE)
        return template.render()

    def describe_receipt_rule_set(self):
        rule_set_name = self._get_param("RuleSetName")

        rule_set = ses_backend.describe_receipt_rule_set(rule_set_name)

        for i, rule in enumerate(rule_set):
            formatted_rule = {}

            for k, v in rule.items():
                self._parse_param(k, v, formatted_rule)

            rule_set[i] = formatted_rule

        template = self.response_template(DESCRIBE_RECEIPT_RULE_SET)

        return template.render(rule_set=rule_set, rule_set_name=rule_set_name)

    def describe_receipt_rule(self):
        rule_set_name = self._get_param("RuleSetName")
        rule_name = self._get_param("RuleName")

        receipt_rule = ses_backend.describe_receipt_rule(rule_set_name, rule_name)

        rule = {}

        for k, v in receipt_rule.items():
            self._parse_param(k, v, rule)

        template = self.response_template(DESCRIBE_RECEIPT_RULE)
        return template.render(rule=rule)

    def update_receipt_rule(self):
        rule_set_name = self._get_param("RuleSetName")
        rule = self._get_dict_param("Rule.")

        ses_backend.update_receipt_rule(rule_set_name, rule)

        template = self.response_template(UPDATE_RECEIPT_RULE)
        return template.render()


VERIFY_EMAIL_IDENTITY = """<VerifyEmailIdentityResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <VerifyEmailIdentityResult/>
  <ResponseMetadata>
    <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</VerifyEmailIdentityResponse>"""

VERIFY_EMAIL_ADDRESS = """<VerifyEmailAddressResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <VerifyEmailAddressResult/>
  <ResponseMetadata>
    <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</VerifyEmailAddressResponse>"""

LIST_IDENTITIES_RESPONSE = """<ListIdentitiesResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <ListIdentitiesResult>
    <Identities>
        {% for identity in identities %}
          <member>{{ identity }}</member>
        {% endfor %}
    </Identities>
  </ListIdentitiesResult>
  <ResponseMetadata>
    <RequestId>cacecf23-9bf1-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</ListIdentitiesResponse>"""

LIST_VERIFIED_EMAIL_RESPONSE = """<ListVerifiedEmailAddressesResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <ListVerifiedEmailAddressesResult>
    <VerifiedEmailAddresses>
        {% for email in email_addresses %}
          <member>{{ email }}</member>
        {% endfor %}
    </VerifiedEmailAddresses>
  </ListVerifiedEmailAddressesResult>
  <ResponseMetadata>
    <RequestId>cacecf23-9bf1-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</ListVerifiedEmailAddressesResponse>"""

VERIFY_DOMAIN_DKIM_RESPONSE = """<VerifyDomainDkimResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <VerifyDomainDkimResult>
    <DkimTokens>
      <member>vvjuipp74whm76gqoni7qmwwn4w4qusjiainivf6sf</member>
      <member>3frqe7jn4obpuxjpwpolz6ipb3k5nvt2nhjpik2oy</member>
      <member>wrqplteh7oodxnad7hsl4mixg2uavzneazxv5sxi2</member>
    </DkimTokens>
    </VerifyDomainDkimResult>
    <ResponseMetadata>
      <RequestId>9662c15b-c469-11e1-99d1-797d6ecd6414</RequestId>
    </ResponseMetadata>
</VerifyDomainDkimResponse>"""

VERIFY_DOMAIN_IDENTITY_RESPONSE = """\
<VerifyDomainIdentityResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <VerifyDomainIdentityResult>
    <VerificationToken>QTKknzFg2J4ygwa+XvHAxUl1hyHoY0gVfZdfjIedHZ0=</VerificationToken>
  </VerifyDomainIdentityResult>
  <ResponseMetadata>
    <RequestId>94f6368e-9bf2-11e1-8ee7-c98a0037a2b6</RequestId>
  </ResponseMetadata>
</VerifyDomainIdentityResponse>"""

DELETE_IDENTITY_RESPONSE = """<DeleteIdentityResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <DeleteIdentityResult/>
  <ResponseMetadata>
    <RequestId>d96bd874-9bf2-11e1-8ee7-c98a0037a2b6</RequestId>
  </ResponseMetadata>
</DeleteIdentityResponse>"""

SEND_EMAIL_RESPONSE = """<SendEmailResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <SendEmailResult>
    <MessageId>{{ message.id }}</MessageId>
  </SendEmailResult>
  <ResponseMetadata>
    <RequestId>d5964849-c866-11e0-9beb-01a62d68c57f</RequestId>
  </ResponseMetadata>
</SendEmailResponse>"""

SEND_TEMPLATED_EMAIL_RESPONSE = """<SendTemplatedEmailResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <SendTemplatedEmailResult>
    <MessageId>{{ message.id }}</MessageId>
  </SendTemplatedEmailResult>
  <ResponseMetadata>
    <RequestId>d5964849-c866-11e0-9beb-01a62d68c57f</RequestId>
  </ResponseMetadata>
</SendTemplatedEmailResponse>"""

SEND_RAW_EMAIL_RESPONSE = """<SendRawEmailResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <SendRawEmailResult>
    <MessageId>{{ message.id }}</MessageId>
  </SendRawEmailResult>
  <ResponseMetadata>
    <RequestId>e0abcdfa-c866-11e0-b6d0-273d09173b49</RequestId>
  </ResponseMetadata>
</SendRawEmailResponse>"""

GET_SEND_QUOTA_RESPONSE = """<GetSendQuotaResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <GetSendQuotaResult>
    <SentLast24Hours>{{ quota.sent_past_24 }}</SentLast24Hours>
    <Max24HourSend>200.0</Max24HourSend>
    <MaxSendRate>1.0</MaxSendRate>
  </GetSendQuotaResult>
  <ResponseMetadata>
    <RequestId>273021c6-c866-11e0-b926-699e21c3af9e</RequestId>
  </ResponseMetadata>
</GetSendQuotaResponse>"""

GET_IDENTITY_NOTIFICATION_ATTRIBUTES = """<GetIdentityNotificationAttributesResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <GetIdentityNotificationAttributesResult>
    <NotificationAttributes>
    {% for identity, config in identities.items() %}
      <entry>
        <key>{{ identity }}</key>
        <value>
          <HeadersInBounceNotificationsEnabled>false</HeadersInBounceNotificationsEnabled>
          <HeadersInDeliveryNotificationsEnabled>false</HeadersInDeliveryNotificationsEnabled>
          <HeadersInComplaintNotificationsEnabled>false</HeadersInComplaintNotificationsEnabled>
          {% if config.get("feedback_forwarding_enabled", True) == False %}
          <ForwardingEnabled>false</ForwardingEnabled>
          {% else %}
          <ForwardingEnabled>true</ForwardingEnabled>
          {% endif %}
        </value>
      </entry>
      {% endfor %}
    </NotificationAttributes>
  </GetIdentityNotificationAttributesResult>
  <ResponseMetadata>
    <RequestId>46c90cfc-9055-4b84-96e3-4d6a309a8b9b</RequestId>
  </ResponseMetadata>
</GetIdentityNotificationAttributesResponse>"""

SET_IDENTITY_FORWARDING_ENABLED_RESPONSE = """<SetIdentityFeedbackForwardingEnabledResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <SetIdentityFeedbackForwardingEnabledResult/>
  <ResponseMetadata>
    <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</SetIdentityFeedbackForwardingEnabledResponse>"""

SET_IDENTITY_NOTIFICATION_TOPIC_RESPONSE = """<SetIdentityNotificationTopicResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <SetIdentityNotificationTopicResult/>
  <ResponseMetadata>
    <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</SetIdentityNotificationTopicResponse>"""

GET_SEND_STATISTICS = """<GetSendStatisticsResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <GetSendStatisticsResult>
      <SendDataPoints>
        {% for statistics in all_statistics %}
            <item>
                <DeliveryAttempts>{{ statistics["DeliveryAttempts"] }}</DeliveryAttempts>
                <Rejects>{{ statistics["Rejects"] }}</Rejects>
                <Bounces>{{ statistics["Bounces"] }}</Bounces>
                <Complaints>{{ statistics["Complaints"] }}</Complaints>
                <Timestamp>{{ statistics["Timestamp"] }}</Timestamp>
            </item>
        {% endfor %}
      </SendDataPoints>
  </GetSendStatisticsResult>
  <ResponseMetadata>
    <RequestId>e0abcdfa-c866-11e0-b6d0-273d09173z49</RequestId>
  </ResponseMetadata>
</GetSendStatisticsResponse>"""

CREATE_CONFIGURATION_SET = """<CreateConfigurationSetResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <CreateConfigurationSetResult/>
  <ResponseMetadata>
    <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</CreateConfigurationSetResponse>"""


CREATE_CONFIGURATION_SET_EVENT_DESTINATION = """<CreateConfigurationSetEventDestinationResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <CreateConfigurationSetEventDestinationResult/>
  <ResponseMetadata>
    <RequestId>67e0ef1a-9bf2-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</CreateConfigurationSetEventDestinationResponse>"""

CREATE_TEMPLATE = """<CreateTemplateResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <CreateTemplateResult/>
  <ResponseMetadata>
    <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf12ba</RequestId>
  </ResponseMetadata>
</CreateTemplateResponse>"""

UPDATE_TEMPLATE = """<UpdateTemplateResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <UpdateTemplateResult/>
  <ResponseMetadata>
    <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf12ba</RequestId>
  </ResponseMetadata>
</UpdateTemplateResponse>"""

GET_TEMPLATE = """<GetTemplateResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
    <GetTemplateResult>
        <Template>
            <TemplateName>{{ template_data["template_name"] }}</TemplateName>
            <SubjectPart>{{ template_data["subject_part"] }}</SubjectPart>
            <HtmlPart><![CDATA[{{ template_data["html_part"] }}]]></HtmlPart>
            <TextPart>{{ template_data["text_part"] }}</TextPart>
        </Template>
    </GetTemplateResult>
    <ResponseMetadata>
        <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf12ba</RequestId>
    </ResponseMetadata>
</GetTemplateResponse>"""


LIST_TEMPLATES = """<ListTemplatesResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
    <ListTemplatesResult>
        <TemplatesMetadata>
            {% for template in templates %}
                <Item>
                    <Name>{{ template["template_name"] }}</Name>
                    <CreatedTimestamp>{{ template["Timestamp"] }}</CreatedTimestamp>
                </Item>
            {% endfor %}
        </TemplatesMetadata>
    </ListTemplatesResult>
    <ResponseMetadata>
        <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf12ba</RequestId>
    </ResponseMetadata>
</ListTemplatesResponse>"""

RENDER_TEMPLATE = """
<TestRenderTemplateResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
    <TestRenderTemplateResult>
      <RenderedTemplate>
      {{template | e}}
      </RenderedTemplate>
    </TestRenderTemplateResult>
    <ResponseMetadata>
        <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf12ba</RequestId>
    </ResponseMetadata>
</TestRenderTemplateResponse>
"""

CREATE_RECEIPT_RULE_SET = """<CreateReceiptRuleSetResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <CreateReceiptRuleSetResult/>
  <ResponseMetadata>
    <RequestId>47e0ef1a-9bf2-11e1-9279-01ab88cf109a</RequestId>
  </ResponseMetadata>
</CreateReceiptRuleSetResponse>"""

CREATE_RECEIPT_RULE = """<CreateReceiptRuleResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <CreateReceiptRuleResult/>
  <ResponseMetadata>
    <RequestId>15e0ef1a-9bf2-11e1-9279-01ab88cf109a</RequestId>
  </ResponseMetadata>
</CreateReceiptRuleResponse>"""

DESCRIBE_RECEIPT_RULE_SET = """<DescribeReceiptRuleSetResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <DescribeReceiptRuleSetResult>
    <Rules>
      {% for rule in rule_set %}
      <member>
        <Recipients>
          {% for recipient in rule["recipients"] %}
          <member>{{recipient}}</member>
          {% endfor %}
        </Recipients>
        <Name>{{rule["name"]}}</Name>
        <Actions>
          {% for action in rule["actions"] %}
          <member>
            {% if action["_s3_action"] %}
            <S3Action>
              <BucketName>{{action["_s3_action"]["_bucket_name"]}}</BucketName>
              <KmsKeyArn>{{action["_s3_action"]["_kms_key_arn"]}}</KmsKeyArn>
              <ObjectKeyPrefix>{{action["_s3_action"]["_object_key_prefix"]}}</ObjectKeyPrefix>
              <TopicArn>{{action["_s3_action"]["_topic_arn"]}}</TopicArn>
            </S3Action>
            {% endif %}
            {% if action["_bounce_action"] %}
            <BounceAction>
              <TopicArn>{{action["_bounce_action"]["_topic_arn"]}}</TopicArn>
              <SmtpReplyCode>{{action["_bounce_action"]["_smtp_reply_code"]}}</SmtpReplyCode>
              <StatusCode>{{action["_bounce_action"]["_status_code"]}}</StatusCode>
              <Message>{{action["_bounce_action"]["_message"]}}</Message>
              <Sender>{{action["_bounce_action"]["_sender"]}}</Sender>
            </BounceAction>
            {% endif %}
          </member>
          {% endfor %}
        </Actions>
        <TlsPolicy>{{rule["tls_policy"]}}</TlsPolicy>
        <ScanEnabled>{{rule["scan_enabled"]}}</ScanEnabled>
        <Enabled>{{rule["enabled"]}}</Enabled>
      </member>
      {% endfor %}
    </Rules>
    <Metadata>
      <Name>{{rule_set_name}}</Name>
      <CreatedTimestamp>2021-10-31</CreatedTimestamp>
    </Metadata>
  </DescribeReceiptRuleSetResult>
  <ResponseMetadata>
    <RequestId>15e0ef1a-9bf2-11e1-9279-01ab88cf109a</RequestId>
  </ResponseMetadata>
</DescribeReceiptRuleSetResponse>
"""

DESCRIBE_RECEIPT_RULE = """<DescribeReceiptRuleResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <DescribeReceiptRuleResult>
    <Rule>
      <Recipients>
        {% for recipient in rule["recipients"] %}
        <member>{{recipient}}</member>
        {% endfor %}
      </Recipients>
      <Name>{{rule["name"]}}</Name>
      <Actions>
        {% for action in rule["actions"] %}
        <member>
          {% if action["_s3_action"] %}
          <S3Action>
            <BucketName>{{action["_s3_action"]["_bucket_name"]}}</BucketName>
            <KmsKeyArn>{{action["_s3_action"]["_kms_key_arn"]}}</KmsKeyArn>
            <ObjectKeyPrefix>{{action["_s3_action"]["_object_key_prefix"]}}</ObjectKeyPrefix>
            <TopicArn>{{action["_s3_action"]["_topic_arn"]}}</TopicArn>
          </S3Action>
          {% endif %}
          {% if action["_bounce_action"] %}
          <BounceAction>
            <TopicArn>{{action["_bounce_action"]["_topic_arn"]}}</TopicArn>
            <SmtpReplyCode>{{action["_bounce_action"]["_smtp_reply_code"]}}</SmtpReplyCode>
            <StatusCode>{{action["_bounce_action"]["_status_code"]}}</StatusCode>
            <Message>{{action["_bounce_action"]["_message"]}}</Message>
            <Sender>{{action["_bounce_action"]["_sender"]}}</Sender>
          </BounceAction>
          {% endif %}
        </member>
        {% endfor %}
      </Actions>
      <TlsPolicy>{{rule["tls_policy"]}}</TlsPolicy>
      <ScanEnabled>{{rule["scan_enabled"]}}</ScanEnabled>
      <Enabled>{{rule["enabled"]}}</Enabled>
    </Rule>
  </DescribeReceiptRuleResult>
  <ResponseMetadata>
    <RequestId>15e0ef1a-9bf2-11e1-9279-01ab88cf109a</RequestId>
  </ResponseMetadata>
</DescribeReceiptRuleResponse>
"""

UPDATE_RECEIPT_RULE = """<UpdateReceiptRuleResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <UpdateReceiptRuleResult/>
  <ResponseMetadata>
    <RequestId>15e0ef1a-9bf2-11e1-9279-01ab88cf109a</RequestId>
  </ResponseMetadata>
</UpdateReceiptRuleResponse>"""
