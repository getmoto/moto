from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError
from six.moves.email_mime_multipart import MIMEMultipart
from six.moves.email_mime_text import MIMEText

import sure  # noqa

from moto import mock_ses


@mock_ses
def test_verify_email_identity():
    conn = boto3.client('ses', region_name='us-east-1')
    conn.verify_email_identity(EmailAddress="test@example.com")

    identities = conn.list_identities()
    address = identities['Identities'][0]
    address.should.equal('test@example.com')

@mock_ses
def test_verify_email_address():
    conn = boto3.client('ses', region_name='us-east-1')
    conn.verify_email_address(EmailAddress="test@example.com")
    email_addresses = conn.list_verified_email_addresses()
    email = email_addresses['VerifiedEmailAddresses'][0]
    email.should.equal('test@example.com')

@mock_ses
def test_domain_verify():
    conn = boto3.client('ses', region_name='us-east-1')

    conn.verify_domain_dkim(Domain="domain1.com")
    conn.verify_domain_identity(Domain="domain2.com")

    identities = conn.list_identities()
    domains = list(identities['Identities'])
    domains.should.equal(['domain1.com', 'domain2.com'])


@mock_ses
def test_delete_identity():
    conn = boto3.client('ses', region_name='us-east-1')
    conn.verify_email_identity(EmailAddress="test@example.com")

    conn.list_identities()['Identities'].should.have.length_of(1)
    conn.delete_identity(Identity="test@example.com")
    conn.list_identities()['Identities'].should.have.length_of(0)


@mock_ses
def test_send_email():
    conn = boto3.client('ses', region_name='us-east-1')

    kwargs = dict(
        Source="test@example.com",
        Destination={
            "ToAddresses": ["test_to@example.com"],
            "CcAddresses": ["test_cc@example.com"],
            "BccAddresses": ["test_bcc@example.com"],
        },
        Message={
            "Subject": {"Data": "test subject"},
            "Body": {"Text": {"Data": "test body"}}
        }
    )
    conn.send_email.when.called_with(**kwargs).should.throw(ClientError)

    conn.verify_domain_identity(Domain='example.com')
    conn.send_email(**kwargs)

    too_many_addresses = list('to%s@example.com' % i for i in range(51))
    conn.send_email.when.called_with(
        **dict(kwargs, Destination={'ToAddresses': too_many_addresses})
    ).should.throw(ClientError)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota['SentLast24Hours'])
    sent_count.should.equal(3)


@mock_ses
def test_send_html_email():
    conn = boto3.client('ses', region_name='us-east-1')

    kwargs = dict(
        Source="test@example.com",
        Destination={
            "ToAddresses": ["test_to@example.com"]
        },
        Message={
            "Subject": {"Data": "test subject"},
            "Body": {"Html": {"Data": "test body"}}
        }
    )

    conn.send_email.when.called_with(**kwargs).should.throw(ClientError)

    conn.verify_email_identity(EmailAddress="test@example.com")
    conn.send_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota['SentLast24Hours'])
    sent_count.should.equal(1)


@mock_ses
def test_send_raw_email():
    conn = boto3.client('ses', region_name='us-east-1')

    message = MIMEMultipart()
    message['Subject'] = 'Test'
    message['From'] = 'test@example.com'
    message['To'] = 'to@example.com, foo@example.com'

    # Message body
    part = MIMEText('test file attached')
    message.attach(part)

    # Attachment
    part = MIMEText('contents of test file here')
    part.add_header('Content-Disposition', 'attachment; filename=test.txt')
    message.attach(part)

    kwargs = dict(
        Source=message['From'],
        RawMessage={'Data': message.as_string()},
    )

    conn.send_raw_email.when.called_with(**kwargs).should.throw(ClientError)

    conn.verify_email_identity(EmailAddress="test@example.com")
    conn.send_raw_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota['SentLast24Hours'])
    sent_count.should.equal(2)


@mock_ses
def test_send_raw_email_without_source():
    conn = boto3.client('ses', region_name='us-east-1')

    message = MIMEMultipart()
    message['Subject'] = 'Test'
    message['From'] = 'test@example.com'
    message['To'] = 'to@example.com, foo@example.com'

    # Message body
    part = MIMEText('test file attached')
    message.attach(part)

    # Attachment
    part = MIMEText('contents of test file here')
    part.add_header('Content-Disposition', 'attachment; filename=test.txt')
    message.attach(part)

    kwargs = dict(
        RawMessage={'Data': message.as_string()},
    )

    conn.send_raw_email.when.called_with(**kwargs).should.throw(ClientError)

    conn.verify_email_identity(EmailAddress="test@example.com")
    conn.send_raw_email(**kwargs)

    send_quota = conn.get_send_quota()
    sent_count = int(send_quota['SentLast24Hours'])
    sent_count.should.equal(2)


@mock_ses
def test_send_raw_email_without_source_or_from():
    conn = boto3.client('ses', region_name='us-east-1')

    message = MIMEMultipart()
    message['Subject'] = 'Test'
    message['To'] = 'to@example.com, foo@example.com'

    # Message body
    part = MIMEText('test file attached')
    message.attach(part)
    # Attachment
    part = MIMEText('contents of test file here')
    part.add_header('Content-Disposition', 'attachment; filename=test.txt')
    message.attach(part)

    kwargs = dict(
        RawMessage={'Data': message.as_string()},
    )

    conn.send_raw_email.when.called_with(**kwargs).should.throw(ClientError)

