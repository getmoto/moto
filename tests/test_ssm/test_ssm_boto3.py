from __future__ import unicode_literals

import boto3
import sure   # noqa

from moto import mock_ssm


@mock_ssm
def test_delete_parameter():
    client = boto3.client('ssm', region_name='us-east-1')

    client.put_parameter(
        Name='test',
        Description='A test parameter',
        Value='value',
        Type='String')

    response = client.get_parameters(Names=['test'])
    len(response['Parameters']).should.equal(1)

    client.delete_parameter(Name='test')

    response = client.get_parameters(Names=['test'])
    len(response['Parameters']).should.equal(0)


@mock_ssm
def test_put_parameter():
    client = boto3.client('ssm', region_name='us-east-1')

    client.put_parameter(
        Name='test',
        Description='A test parameter',
        Value='value',
        Type='String')

    response = client.get_parameters(
        Names=[
            'test'
        ],
        WithDecryption=False)

    len(response['Parameters']).should.equal(1)
    response['Parameters'][0]['Name'].should.equal('test')
    response['Parameters'][0]['Value'].should.equal('value')
    response['Parameters'][0]['Type'].should.equal('String')


@mock_ssm
def test_describe_parameters():
    client = boto3.client('ssm', region_name='us-east-1')

    client.put_parameter(
        Name='test',
        Description='A test parameter',
        Value='value',
        Type='String')

    response = client.describe_parameters()

    len(response['Parameters']).should.equal(1)
    response['Parameters'][0]['Name'].should.equal('test')
    response['Parameters'][0]['Type'].should.equal('String')


@mock_ssm
def test_describe_parameters_paging():
    client = boto3.client('ssm', region_name='us-east-1')

    for i in range(50):
        client.put_parameter(
            Name="param-%d" % i,
            Value="value-%d" % i,
            Type="String"
        )

    response = client.describe_parameters()
    len(response['Parameters']).should.equal(10)
    response['NextToken'].should.equal('10')

    response = client.describe_parameters(NextToken=response['NextToken'])
    len(response['Parameters']).should.equal(10)
    response['NextToken'].should.equal('20')

    response = client.describe_parameters(NextToken=response['NextToken'])
    len(response['Parameters']).should.equal(10)
    response['NextToken'].should.equal('30')

    response = client.describe_parameters(NextToken=response['NextToken'])
    len(response['Parameters']).should.equal(10)
    response['NextToken'].should.equal('40')

    response = client.describe_parameters(NextToken=response['NextToken'])
    len(response['Parameters']).should.equal(10)
    response['NextToken'].should.equal('50')

    response = client.describe_parameters(NextToken=response['NextToken'])
    len(response['Parameters']).should.equal(0)
    ''.should.equal(response.get('NextToken', ''))


@mock_ssm
def test_describe_parameters_filter_names():
    client = boto3.client('ssm', region_name='us-east-1')

    for i in range(50):
        p = {
            'Name': "param-%d" % i,
            'Value': "value-%d" % i,
            'Type': "String"
        }
        if i % 5 == 0:
            p['Type'] = 'SecureString'
            p['KeyId'] = 'a key'
        client.put_parameter(**p)

    response = client.describe_parameters(Filters=[
        {
            'Key': 'Name',
            'Values': ['param-22']
        },
    ])
    len(response['Parameters']).should.equal(1)
    response['Parameters'][0]['Name'].should.equal('param-22')
    response['Parameters'][0]['Type'].should.equal('String')
    ''.should.equal(response.get('NextToken', ''))


@mock_ssm
def test_describe_parameters_filter_type():
    client = boto3.client('ssm', region_name='us-east-1')

    for i in range(50):
        p = {
            'Name': "param-%d" % i,
            'Value': "value-%d" % i,
            'Type': "String"
        }
        if i % 5 == 0:
            p['Type'] = 'SecureString'
            p['KeyId'] = 'a key'
        client.put_parameter(**p)


    response = client.describe_parameters(Filters=[
        {
            'Key': 'Type',
            'Values': ['SecureString']
        },
    ])
    len(response['Parameters']).should.equal(10)
    response['Parameters'][0]['Type'].should.equal('SecureString')
    '10'.should.equal(response.get('NextToken', ''))


@mock_ssm
def test_describe_parameters_filter_keyid():
    client = boto3.client('ssm', region_name='us-east-1')

    for i in range(50):
        p = {
            'Name': "param-%d" % i,
            'Value': "value-%d" % i,
            'Type': "String"
        }
        if i % 5 == 0:
            p['Type'] = 'SecureString'
            p['KeyId'] = "key:%d" % i
        client.put_parameter(**p)


    response = client.describe_parameters(Filters=[
        {
            'Key': 'KeyId',
            'Values': ['key:10']
        },
    ])
    len(response['Parameters']).should.equal(1)
    response['Parameters'][0]['Name'].should.equal('param-10')
    response['Parameters'][0]['Type'].should.equal('SecureString')
    ''.should.equal(response.get('NextToken', ''))


@mock_ssm
def test_put_parameter_secure_default_kms():
    client = boto3.client('ssm', region_name='us-east-1')

    client.put_parameter(
        Name='test',
        Description='A test parameter',
        Value='value',
        Type='SecureString')

    response = client.get_parameters(
        Names=[
            'test'
        ],
        WithDecryption=False)

    len(response['Parameters']).should.equal(1)
    response['Parameters'][0]['Name'].should.equal('test')
    response['Parameters'][0]['Value'].should.equal('kms:default:value')
    response['Parameters'][0]['Type'].should.equal('SecureString')

    response = client.get_parameters(
        Names=[
            'test'
        ],
        WithDecryption=True)

    len(response['Parameters']).should.equal(1)
    response['Parameters'][0]['Name'].should.equal('test')
    response['Parameters'][0]['Value'].should.equal('value')
    response['Parameters'][0]['Type'].should.equal('SecureString')


@mock_ssm
def test_put_parameter_secure_custom_kms():
    client = boto3.client('ssm', region_name='us-east-1')

    client.put_parameter(
        Name='test',
        Description='A test parameter',
        Value='value',
        Type='SecureString',
        KeyId='foo')

    response = client.get_parameters(
        Names=[
            'test'
        ],
        WithDecryption=False)

    len(response['Parameters']).should.equal(1)
    response['Parameters'][0]['Name'].should.equal('test')
    response['Parameters'][0]['Value'].should.equal('kms:foo:value')
    response['Parameters'][0]['Type'].should.equal('SecureString')

    response = client.get_parameters(
        Names=[
            'test'
        ],
        WithDecryption=True)

    len(response['Parameters']).should.equal(1)
    response['Parameters'][0]['Name'].should.equal('test')
    response['Parameters'][0]['Value'].should.equal('value')
    response['Parameters'][0]['Type'].should.equal('SecureString')
