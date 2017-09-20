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


@mock_sns
def test_list_opted_out():
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.list_phone_numbers_opted_out()

    response.should.contain('phoneNumbers')
    len(response['phoneNumbers']).should.be.greater_than(0)


@mock_sns
def test_opt_in():
    conn = boto3.client('sns', region_name='us-east-1')
    response = conn.list_phone_numbers_opted_out()
    current_len = len(response['phoneNumbers'])
    assert current_len > 0

    conn.opt_in_phone_number(phoneNumber=response['phoneNumbers'][0])

    response = conn.list_phone_numbers_opted_out()
    len(response['phoneNumbers']).should.be.greater_than(0)
    len(response['phoneNumbers']).should.be.lower_than(current_len)


@mock_sns
def test_add_remove_permissions():
    conn = boto3.client('sns', region_name='us-east-1')

    conn.add_permission(
        TopicArn='arn:aws:sns:us-east-1:000000000000:terry_test',
        Label='Test1234',
        AWSAccountId=['999999999999'],
        ActionName=['AddPermission']
    )
    conn.remove_permission(
        TopicArn='arn:aws:sns:us-east-1:000000000000:terry_test',
        Label='Test1234'
    )
