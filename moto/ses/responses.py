from __future__ import unicode_literals
import base64

import six

from moto.core.responses import BaseResponse
from .models import ses_backend


class EmailResponse(BaseResponse):

    def verify_email_identity(self):
        address = self.querystring.get('EmailAddress')[0]
        ses_backend.verify_email_identity(address)
        template = self.response_template(VERIFY_EMAIL_IDENTITY)
        return template.render()

    def verify_email_address(self):
        address = self.querystring.get('EmailAddress')[0]
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
        domain = self.querystring.get('Domain')[0]
        ses_backend.verify_domain(domain)
        template = self.response_template(VERIFY_DOMAIN_DKIM_RESPONSE)
        return template.render()

    def verify_domain_identity(self):
        domain = self.querystring.get('Domain')[0]
        ses_backend.verify_domain(domain)
        template = self.response_template(VERIFY_DOMAIN_IDENTITY_RESPONSE)
        return template.render()

    def delete_identity(self):
        domain = self.querystring.get('Identity')[0]
        ses_backend.delete_identity(domain)
        template = self.response_template(DELETE_IDENTITY_RESPONSE)
        return template.render()

    def send_email(self):
        bodydatakey = 'Message.Body.Text.Data'
        if 'Message.Body.Html.Data' in self.querystring:
            bodydatakey = 'Message.Body.Html.Data'
        body = self.querystring.get(bodydatakey)[0]
        source = self.querystring.get('Source')[0]
        subject = self.querystring.get('Message.Subject.Data')[0]
        destinations = {
            'ToAddresses': [],
            'CcAddresses': [],
            'BccAddresses': [],
        }
        for dest_type in destinations:
            # consume up to 51 to allow exception
            for i in six.moves.range(1, 52):
                field = 'Destination.%s.member.%s' % (dest_type, i)
                address = self.querystring.get(field)
                if address is None:
                    break
                destinations[dest_type].append(address[0])

        message = ses_backend.send_email(source, subject, body, destinations)
        template = self.response_template(SEND_EMAIL_RESPONSE)
        return template.render(message=message)

    def send_raw_email(self):
        source = self.querystring.get('Source')
        if source is not None:
            source, = source

        raw_data = self.querystring.get('RawMessage.Data')[0]
        raw_data = base64.b64decode(raw_data)
        if six.PY3:
            raw_data = raw_data.decode('utf-8')
        destinations = []
        # consume up to 51 to allow exception
        for i in six.moves.range(1, 52):
            field = 'Destinations.member.%s' % i
            address = self.querystring.get(field)
            if address is None:
                break
            destinations.append(address[0])

        message = ses_backend.send_raw_email(source, destinations, raw_data)
        template = self.response_template(SEND_RAW_EMAIL_RESPONSE)
        return template.render(message=message)

    def get_send_quota(self):
        quota = ses_backend.get_send_quota()
        template = self.response_template(GET_SEND_QUOTA_RESPONSE)
        return template.render(quota=quota)


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
