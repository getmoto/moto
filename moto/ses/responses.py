from jinja2 import Template

from moto.core.responses import BaseResponse
from .models import ses_backend


class EmailResponse(BaseResponse):

    def verify_email_identity(self):
        address = self.querystring.get('EmailAddress')[0]
        ses_backend.verify_email_identity(address)
        template = Template(VERIFY_EMAIL_IDENTITY)
        return template.render()

    def list_identities(self):
        identities = ses_backend.list_identities()
        template = Template(LIST_IDENTITIES_RESPONSE)
        return template.render(identities=identities)

    def verify_domain_dkim(self):
        domain = self.querystring.get('Domain')[0]
        ses_backend.verify_domain(domain)
        template = Template(VERIFY_DOMAIN_DKIM_RESPONSE)
        return template.render()

    def verify_domain_identity(self):
        domain = self.querystring.get('Domain')[0]
        ses_backend.verify_domain(domain)
        template = Template(VERIFY_DOMAIN_DKIM_RESPONSE)
        return template.render()

    def delete_identity(self):
        domain = self.querystring.get('Identity')[0]
        ses_backend.delete_identity(domain)
        template = Template(DELETE_IDENTITY_RESPONSE)
        return template.render()

    def send_email(self):
        bodydatakey = 'Message.Body.Text.Data'
        if 'Message.Body.Html.Data' in self.querystring:
            bodydatakey = 'Message.Body.Html.Data'
        body = self.querystring.get(bodydatakey)[0]
        source = self.querystring.get('Source')[0]
        subject = self.querystring.get('Message.Subject.Data')[0]
        destination = self.querystring.get('Destination.ToAddresses.member.1')[0]
        message = ses_backend.send_email(source, subject, body, destination)
        if not message:
            return "Did not have authority to send from email {0}".format(source), dict(status=400)
        template = Template(SEND_EMAIL_RESPONSE)
        return template.render(message=message)

    def send_raw_email(self):
        source = self.querystring.get('Source')[0]
        destination = self.querystring.get('Destinations.member.1')[0]
        raw_data = self.querystring.get('RawMessage.Data')[0]

        message = ses_backend.send_raw_email(source, destination, raw_data)
        if not message:
            return "Did not have authority to send from email {0}".format(source), dict(status=400)
        template = Template(SEND_RAW_EMAIL_RESPONSE)
        return template.render(message=message)

    def get_send_quota(self):
        quota = ses_backend.get_send_quota()
        template = Template(GET_SEND_QUOTA_RESPONSE)
        return template.render(quota=quota)


VERIFY_EMAIL_IDENTITY = """<VerifyEmailIdentityResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
  <VerifyEmailIdentityResult/>
  <ResponseMetadata>
    <RequestId>47e0ef1a-9bf2-11e1-9279-0100e8cf109a</RequestId>
  </ResponseMetadata>
</VerifyEmailIdentityResponse>"""

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
