from __future__ import unicode_literals
import boto3
import sure  # noqa

from moto import mock_sns


@mock_sns
def test_set_sms_attributes():
    conn = boto3.client('sns', region_name='us-east-1')

    conn.set_sms_attributes(attributes={'DefaultSMSType': 'Transactional', 'test': 'test'})

    response = conn.get_sms_attributes()
    response.should.contain('attributes')
    response['attributes'].should.contain('DefaultSMSType')
    response['attributes'].should.contain('test')
    response['attributes']['DefaultSMSType'].should.equal('Transactional')
    response['attributes']['test'].should.equal('test')


@mock_sns
def test_get_sms_attributes_filtered():
    conn = boto3.client('sns', region_name='us-east-1')

    conn.set_sms_attributes(attributes={'DefaultSMSType': 'Transactional', 'test': 'test'})

    response = conn.get_sms_attributes(attributes=['DefaultSMSType'])
    response.should.contain('attributes')
    response['attributes'].should.contain('DefaultSMSType')
    response['attributes'].should_not.contain('test')
    response['attributes']['DefaultSMSType'].should.equal('Transactional')
