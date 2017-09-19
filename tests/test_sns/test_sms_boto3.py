from __future__ import unicode_literals
import boto3
import sure  # noqa

from moto import mock_sns
from botocore.exceptions import ClientError
from nose.tools import assert_raises


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


@mock_sns
def test_check_not_opted_out():
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.check_if_phone_number_is_opted_out(phoneNumber='+447428545375')

    response.should.contain('isOptedOut')
    response['isOptedOut'].should.be(False)


@mock_sns
def test_check_opted_out():  # Ends in 99 so is opted out
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.check_if_phone_number_is_opted_out(phoneNumber='+447428545399')

    response.should.contain('isOptedOut')
    response['isOptedOut'].should.be(True)


@mock_sns
def test_check_opted_out_invalid():
    conn = boto3.client('sns', region_name='us-east-1')

    # Invalid phone number
    with assert_raises(ClientError):
        conn.check_if_phone_number_is_opted_out(phoneNumber='+44742LALALA')
