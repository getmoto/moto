from __future__ import unicode_literals

import os
import boto3
from freezegun import freeze_time
import sure  # noqa
import uuid

from botocore.exceptions import ClientError

from moto import mock_acm


RESOURCE_FOLDER = os.path.join(os.path.dirname(__file__), 'resources')
_GET_RESOURCE = lambda x: open(os.path.join(RESOURCE_FOLDER, x), 'rb').read()
CA_CRT = _GET_RESOURCE('ca.pem')
CA_KEY = _GET_RESOURCE('ca.key')
SERVER_CRT = _GET_RESOURCE('star_moto_com.pem')
SERVER_COMMON_NAME = '*.moto.com'
SERVER_CRT_BAD = _GET_RESOURCE('star_moto_com-bad.pem')
SERVER_KEY = _GET_RESOURCE('star_moto_com.key')
BAD_ARN = 'arn:aws:acm:us-east-2:123456789012:certificate/_0000000-0000-0000-0000-000000000000'


def _import_cert(client):
    response = client.import_certificate(
        Certificate=SERVER_CRT,
        PrivateKey=SERVER_KEY,
        CertificateChain=CA_CRT
    )
    return response['CertificateArn']


# Also tests GetCertificate
@mock_acm
def test_import_certificate():
    client = boto3.client('acm', region_name='eu-central-1')

    resp = client.import_certificate(
        Certificate=SERVER_CRT,
        PrivateKey=SERVER_KEY,
        CertificateChain=CA_CRT
    )
    resp = client.get_certificate(CertificateArn=resp['CertificateArn'])

    resp['Certificate'].should.equal(SERVER_CRT.decode())
    resp.should.contain('CertificateChain')


@mock_acm
def test_import_bad_certificate():
    client = boto3.client('acm', region_name='eu-central-1')

    try:
        client.import_certificate(
            Certificate=SERVER_CRT_BAD,
            PrivateKey=SERVER_KEY,
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ValidationException')
    else:
        raise RuntimeError('Should of raised ValidationException')


@mock_acm
def test_list_certificates():
    client = boto3.client('acm', region_name='eu-central-1')
    arn = _import_cert(client)

    resp = client.list_certificates()
    len(resp['CertificateSummaryList']).should.equal(1)

    resp['CertificateSummaryList'][0]['CertificateArn'].should.equal(arn)
    resp['CertificateSummaryList'][0]['DomainName'].should.equal(SERVER_COMMON_NAME)


@mock_acm
def test_list_certificates_by_status():
    client = boto3.client('acm', region_name='eu-central-1')
    issued_arn = _import_cert(client)
    pending_arn = client.request_certificate(DomainName='google.com')['CertificateArn']

    resp = client.list_certificates()
    len(resp['CertificateSummaryList']).should.equal(2)
    resp = client.list_certificates(CertificateStatuses=['EXPIRED', 'INACTIVE'])
    len(resp['CertificateSummaryList']).should.equal(0)
    resp = client.list_certificates(CertificateStatuses=['PENDING_VALIDATION'])
    len(resp['CertificateSummaryList']).should.equal(1)
    resp['CertificateSummaryList'][0]['CertificateArn'].should.equal(pending_arn)

    resp = client.list_certificates(CertificateStatuses=['ISSUED'])
    len(resp['CertificateSummaryList']).should.equal(1)
    resp['CertificateSummaryList'][0]['CertificateArn'].should.equal(issued_arn)
    resp = client.list_certificates(CertificateStatuses=['ISSUED', 'PENDING_VALIDATION'])
    len(resp['CertificateSummaryList']).should.equal(2)
    arns = {cert['CertificateArn'] for cert in resp['CertificateSummaryList']}
    arns.should.contain(issued_arn)
    arns.should.contain(pending_arn)



@mock_acm
def test_get_invalid_certificate():
    client = boto3.client('acm', region_name='eu-central-1')

    try:
        client.get_certificate(CertificateArn=BAD_ARN)
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFoundException')
    else:
        raise RuntimeError('Should of raised ResourceNotFoundException')


# Also tests deleting invalid certificate
@mock_acm
def test_delete_certificate():
    client = boto3.client('acm', region_name='eu-central-1')
    arn = _import_cert(client)

    # If it does not raise an error and the next call does, all is fine
    client.delete_certificate(CertificateArn=arn)

    try:
        client.delete_certificate(CertificateArn=arn)
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFoundException')
    else:
        raise RuntimeError('Should of raised ResourceNotFoundException')


@mock_acm
def test_describe_certificate():
    client = boto3.client('acm', region_name='eu-central-1')
    arn = _import_cert(client)

    resp = client.describe_certificate(CertificateArn=arn)
    resp['Certificate']['CertificateArn'].should.equal(arn)
    resp['Certificate']['DomainName'].should.equal(SERVER_COMMON_NAME)
    resp['Certificate']['Issuer'].should.equal('Moto')
    resp['Certificate']['KeyAlgorithm'].should.equal('RSA_2048')
    resp['Certificate']['Status'].should.equal('ISSUED')
    resp['Certificate']['Type'].should.equal('IMPORTED')


@mock_acm
def test_describe_certificate():
    client = boto3.client('acm', region_name='eu-central-1')

    try:
        client.describe_certificate(CertificateArn=BAD_ARN)
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFoundException')
    else:
        raise RuntimeError('Should of raised ResourceNotFoundException')


# Also tests ListTagsForCertificate
@mock_acm
def test_add_tags_to_certificate():
    client = boto3.client('acm', region_name='eu-central-1')
    arn = _import_cert(client)

    client.add_tags_to_certificate(
        CertificateArn=arn,
        Tags=[
            {'Key': 'key1', 'Value': 'value1'},
            {'Key': 'key2'},
        ]
    )

    resp = client.list_tags_for_certificate(CertificateArn=arn)
    tags = {item['Key']: item.get('Value', '__NONE__') for item in resp['Tags']}

    tags.should.contain('key1')
    tags.should.contain('key2')
    tags['key1'].should.equal('value1')

    # This way, it ensures that we can detect if None is passed back when it shouldnt,
    # as we store keys without values with a value of None, but it shouldnt be passed back
    tags['key2'].should.equal('__NONE__')


@mock_acm
def test_add_tags_to_invalid_certificate():
    client = boto3.client('acm', region_name='eu-central-1')

    try:
        client.add_tags_to_certificate(
            CertificateArn=BAD_ARN,
            Tags=[
                {'Key': 'key1', 'Value': 'value1'},
                {'Key': 'key2'},
            ]
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFoundException')
    else:
        raise RuntimeError('Should of raised ResourceNotFoundException')


@mock_acm
def test_list_tags_for_invalid_certificate():
    client = boto3.client('acm', region_name='eu-central-1')

    try:
        client.list_tags_for_certificate(CertificateArn=BAD_ARN)
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFoundException')
    else:
        raise RuntimeError('Should of raised ResourceNotFoundException')


@mock_acm
def test_remove_tags_from_certificate():
    client = boto3.client('acm', region_name='eu-central-1')
    arn = _import_cert(client)

    client.add_tags_to_certificate(
        CertificateArn=arn,
        Tags=[
            {'Key': 'key1', 'Value': 'value1'},
            {'Key': 'key2'},
            {'Key': 'key3', 'Value': 'value3'},
            {'Key': 'key4', 'Value': 'value4'},
        ]
    )

    client.remove_tags_from_certificate(
        CertificateArn=arn,
        Tags=[
            {'Key': 'key1', 'Value': 'value2'},  # Should not remove as doesnt match
            {'Key': 'key2'},  # Single key removal
            {'Key': 'key3', 'Value': 'value3'},  # Exact match removal
            {'Key': 'key4'}  # Partial match removal
        ]
    )

    resp = client.list_tags_for_certificate(CertificateArn=arn)
    tags = {item['Key']: item.get('Value', '__NONE__') for item in resp['Tags']}

    for key in ('key2', 'key3', 'key4'):
        tags.should_not.contain(key)

    tags.should.contain('key1')


@mock_acm
def test_remove_tags_from_invalid_certificate():
    client = boto3.client('acm', region_name='eu-central-1')

    try:
        client.remove_tags_from_certificate(
            CertificateArn=BAD_ARN,
            Tags=[
                {'Key': 'key1', 'Value': 'value1'},
                {'Key': 'key2'},
            ]
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFoundException')
    else:
        raise RuntimeError('Should of raised ResourceNotFoundException')


@mock_acm
def test_resend_validation_email():
    client = boto3.client('acm', region_name='eu-central-1')
    arn = _import_cert(client)

    client.resend_validation_email(
        CertificateArn=arn,
        Domain='*.moto.com',
        ValidationDomain='NOTUSEDYET'
    )
    # Returns nothing, boto would raise Exceptions otherwise


@mock_acm
def test_resend_validation_email_invalid():
    client = boto3.client('acm', region_name='eu-central-1')
    arn = _import_cert(client)

    try:
        client.resend_validation_email(
            CertificateArn=arn,
            Domain='no-match.moto.com',
            ValidationDomain='NOTUSEDYET'
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('InvalidDomainValidationOptionsException')
    else:
        raise RuntimeError('Should of raised InvalidDomainValidationOptionsException')

    try:
        client.resend_validation_email(
            CertificateArn=BAD_ARN,
            Domain='no-match.moto.com',
            ValidationDomain='NOTUSEDYET'
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ResourceNotFoundException')
    else:
        raise RuntimeError('Should of raised ResourceNotFoundException')


@mock_acm
def test_request_certificate():
    client = boto3.client('acm', region_name='eu-central-1')

    token = str(uuid.uuid4())

    resp = client.request_certificate(
        DomainName='google.com',
        IdempotencyToken=token,
        SubjectAlternativeNames=['google.com', 'www.google.com', 'mail.google.com'],
    )
    resp.should.contain('CertificateArn')
    arn = resp['CertificateArn']
    arn.should.match(r"arn:aws:acm:eu-central-1:\d{12}:certificate/")

    resp = client.request_certificate(
        DomainName='google.com',
        IdempotencyToken=token,
        SubjectAlternativeNames=['google.com', 'www.google.com', 'mail.google.com'],
    )
    resp['CertificateArn'].should.equal(arn)


@mock_acm
def test_request_certificate_no_san():
    client = boto3.client('acm', region_name='eu-central-1')

    resp = client.request_certificate(
        DomainName='google.com'
    )
    resp.should.contain('CertificateArn')

    resp2 = client.describe_certificate(
        CertificateArn=resp['CertificateArn']
    )
    resp2.should.contain('Certificate')

# # Also tests the SAN code
# # requires Pull: https://github.com/spulec/freezegun/pull/210
# @freeze_time("2012-01-01 12:00:00", as_arg=True)
# @mock_acm
# def test_request_certificate(frozen_time):
#     # After requesting a certificate, it should then auto-validate after 1 minute
#     # Some sneaky programming for that ;-)
#     client = boto3.client('acm', region_name='eu-central-1')
#
#     resp = client.request_certificate(
#         DomainName='google.com',
#         SubjectAlternativeNames=['google.com', 'www.google.com', 'mail.google.com'],
#     )
#     arn = resp['CertificateArn']
#
#     resp = client.describe_certificate(CertificateArn=arn)
#     resp['Certificate']['CertificateArn'].should.equal(arn)
#     resp['Certificate']['DomainName'].should.equal('google.com')
#     resp['Certificate']['Issuer'].should.equal('Amazon')
#     resp['Certificate']['KeyAlgorithm'].should.equal('RSA_2048')
#     resp['Certificate']['Status'].should.equal('PENDING_VALIDATION')
#     resp['Certificate']['Type'].should.equal('AMAZON_ISSUED')
#     len(resp['Certificate']['SubjectAlternativeNames']).should.equal(3)
#
#     # Move time
#     frozen_time.move_to('2012-01-01 12:02:00')
#     resp = client.describe_certificate(CertificateArn=arn)
#     resp['Certificate']['CertificateArn'].should.equal(arn)
#     resp['Certificate']['Status'].should.equal('ISSUED')
#
#
# # requires Pull: https://github.com/spulec/freezegun/pull/210
# @freeze_time("2012-01-01 12:00:00", as_arg=True)
# @mock_acm
# def test_request_certificate(frozen_time):
#     # After requesting a certificate, it should then auto-validate after 1 minute
#     # Some sneaky programming for that ;-)
#     client = boto3.client('acm', region_name='eu-central-1')
#
#     resp = client.request_certificate(
#         IdempotencyToken='test_token',
#         DomainName='google.com',
#         SubjectAlternativeNames=['google.com', 'www.google.com', 'mail.google.com'],
#     )
#     original_arn = resp['CertificateArn']
#
#     # Should be able to request a certificate multiple times in an hour
#     # after that it makes a new one
#     for time_intervals in ('2012-01-01 12:15:00', '2012-01-01 12:30:00', '2012-01-01 12:45:00'):
#         frozen_time.move_to(time_intervals)
#         resp = client.request_certificate(
#             IdempotencyToken='test_token',
#             DomainName='google.com',
#             SubjectAlternativeNames=['google.com', 'www.google.com', 'mail.google.com'],
#         )
#         arn = resp['CertificateArn']
#         arn.should.equal(original_arn)
#
#     # Move time
#     frozen_time.move_to('2012-01-01 13:01:00')
#     resp = client.request_certificate(
#         IdempotencyToken='test_token',
#         DomainName='google.com',
#         SubjectAlternativeNames=['google.com', 'www.google.com', 'mail.google.com'],
#     )
#     arn = resp['CertificateArn']
#     arn.should_not.equal(original_arn)
