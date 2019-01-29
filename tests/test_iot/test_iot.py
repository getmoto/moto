from __future__ import unicode_literals

import json
import sure  # noqa
import boto3

from moto import mock_iot
from botocore.exceptions import ClientError
from nose.tools import assert_raises


@mock_iot
def test_things():
    client = boto3.client('iot', region_name='ap-northeast-1')
    name = 'my-thing'
    type_name = 'my-type-name'

    # thing type
    thing_type = client.create_thing_type(thingTypeName=type_name)
    thing_type.should.have.key('thingTypeName').which.should.equal(type_name)
    thing_type.should.have.key('thingTypeArn')

    res = client.list_thing_types()
    res.should.have.key('thingTypes').which.should.have.length_of(1)
    for thing_type in res['thingTypes']:
        thing_type.should.have.key('thingTypeName').which.should_not.be.none

    thing_type = client.describe_thing_type(thingTypeName=type_name)
    thing_type.should.have.key('thingTypeName').which.should.equal(type_name)
    thing_type.should.have.key('thingTypeProperties')
    thing_type.should.have.key('thingTypeMetadata')

    # thing
    thing = client.create_thing(thingName=name, thingTypeName=type_name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')
    res = client.list_things()
    res.should.have.key('things').which.should.have.length_of(1)
    for thing in res['things']:
        thing.should.have.key('thingName').which.should_not.be.none
        thing.should.have.key('thingArn').which.should_not.be.none

    thing = client.update_thing(thingName=name, attributePayload={'attributes': {'k1': 'v1'}})
    res = client.list_things()
    res.should.have.key('things').which.should.have.length_of(1)
    for thing in res['things']:
        thing.should.have.key('thingName').which.should_not.be.none
        thing.should.have.key('thingArn').which.should_not.be.none
    res['things'][0]['attributes'].should.have.key('k1').which.should.equal('v1')

    thing = client.describe_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('defaultClientId')
    thing.should.have.key('thingTypeName')
    thing.should.have.key('attributes')
    thing.should.have.key('version')

    # delete thing
    client.delete_thing(thingName=name)
    res = client.list_things()
    res.should.have.key('things').which.should.have.length_of(0)

    # delete thing type
    client.delete_thing_type(thingTypeName=type_name)
    res = client.list_thing_types()
    res.should.have.key('thingTypes').which.should.have.length_of(0)


@mock_iot
def test_list_thing_types():
    client = boto3.client('iot', region_name='ap-northeast-1')

    for i in range(0, 100):
        client.create_thing_type(thingTypeName=str(i + 1))

    thing_types = client.list_thing_types()
    thing_types.should.have.key('nextToken')
    thing_types.should.have.key('thingTypes').which.should.have.length_of(50)
    thing_types['thingTypes'][0]['thingTypeName'].should.equal('1')
    thing_types['thingTypes'][-1]['thingTypeName'].should.equal('50')

    thing_types = client.list_thing_types(nextToken=thing_types['nextToken'])
    thing_types.should.have.key('thingTypes').which.should.have.length_of(50)
    thing_types.should_not.have.key('nextToken')
    thing_types['thingTypes'][0]['thingTypeName'].should.equal('51')
    thing_types['thingTypes'][-1]['thingTypeName'].should.equal('100')


@mock_iot
def test_list_thing_types_with_typename_filter():
    client = boto3.client('iot', region_name='ap-northeast-1')

    client.create_thing_type(thingTypeName='thing')
    client.create_thing_type(thingTypeName='thingType')
    client.create_thing_type(thingTypeName='thingTypeName')
    client.create_thing_type(thingTypeName='thingTypeNameGroup')
    client.create_thing_type(thingTypeName='shouldNotFind')
    client.create_thing_type(thingTypeName='find me it shall not')

    thing_types = client.list_thing_types(thingTypeName='thing')
    thing_types.should_not.have.key('nextToken')
    thing_types.should.have.key('thingTypes').which.should.have.length_of(4)
    thing_types['thingTypes'][0]['thingTypeName'].should.equal('thing')
    thing_types['thingTypes'][-1]['thingTypeName'].should.equal('thingTypeNameGroup')

    thing_types = client.list_thing_types(thingTypeName='thingTypeName')
    thing_types.should_not.have.key('nextToken')
    thing_types.should.have.key('thingTypes').which.should.have.length_of(2)
    thing_types['thingTypes'][0]['thingTypeName'].should.equal('thingTypeName')
    thing_types['thingTypes'][-1]['thingTypeName'].should.equal('thingTypeNameGroup')


@mock_iot
def test_list_things_with_next_token():
    client = boto3.client('iot', region_name='ap-northeast-1')

    for i in range(0, 200):
        client.create_thing(thingName=str(i + 1))

    things = client.list_things()
    things.should.have.key('nextToken')
    things.should.have.key('things').which.should.have.length_of(50)
    things['things'][0]['thingName'].should.equal('1')
    things['things'][0]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/1')
    things['things'][-1]['thingName'].should.equal('50')
    things['things'][-1]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/50')

    things = client.list_things(nextToken=things['nextToken'])
    things.should.have.key('nextToken')
    things.should.have.key('things').which.should.have.length_of(50)
    things['things'][0]['thingName'].should.equal('51')
    things['things'][0]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/51')
    things['things'][-1]['thingName'].should.equal('100')
    things['things'][-1]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/100')

    things = client.list_things(nextToken=things['nextToken'])
    things.should.have.key('nextToken')
    things.should.have.key('things').which.should.have.length_of(50)
    things['things'][0]['thingName'].should.equal('101')
    things['things'][0]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/101')
    things['things'][-1]['thingName'].should.equal('150')
    things['things'][-1]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/150')

    things = client.list_things(nextToken=things['nextToken'])
    things.should_not.have.key('nextToken')
    things.should.have.key('things').which.should.have.length_of(50)
    things['things'][0]['thingName'].should.equal('151')
    things['things'][0]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/151')
    things['things'][-1]['thingName'].should.equal('200')
    things['things'][-1]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/200')


@mock_iot
def test_list_things_with_attribute_and_thing_type_filter_and_next_token():
    client = boto3.client('iot', region_name='ap-northeast-1')
    client.create_thing_type(thingTypeName='my-thing-type')

    for i in range(0, 200):
        if not (i + 1) % 3:
            attribute_payload = {
                'attributes': {
                    'foo': 'bar'
                }
            }
        elif not (i + 1) % 5:
            attribute_payload = {
                'attributes': {
                    'bar': 'foo'
                }
            }
        else:
            attribute_payload = {}

        if not (i + 1) % 2:
            thing_type_name = 'my-thing-type'
            client.create_thing(thingName=str(i + 1), thingTypeName=thing_type_name, attributePayload=attribute_payload)
        else:
            client.create_thing(thingName=str(i + 1), attributePayload=attribute_payload)

    # Test filter for thingTypeName
    things = client.list_things(thingTypeName=thing_type_name)
    things.should.have.key('nextToken')
    things.should.have.key('things').which.should.have.length_of(50)
    things['things'][0]['thingName'].should.equal('2')
    things['things'][0]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/2')
    things['things'][-1]['thingName'].should.equal('100')
    things['things'][-1]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/100')
    all(item['thingTypeName'] == thing_type_name for item in things['things'])

    things = client.list_things(nextToken=things['nextToken'], thingTypeName=thing_type_name)
    things.should_not.have.key('nextToken')
    things.should.have.key('things').which.should.have.length_of(50)
    things['things'][0]['thingName'].should.equal('102')
    things['things'][0]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/102')
    things['things'][-1]['thingName'].should.equal('200')
    things['things'][-1]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/200')
    all(item['thingTypeName'] == thing_type_name for item in things['things'])

    # Test filter for attributes
    things = client.list_things(attributeName='foo', attributeValue='bar')
    things.should.have.key('nextToken')
    things.should.have.key('things').which.should.have.length_of(50)
    things['things'][0]['thingName'].should.equal('3')
    things['things'][0]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/3')
    things['things'][-1]['thingName'].should.equal('150')
    things['things'][-1]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/150')
    all(item['attributes'] == {'foo': 'bar'} for item in things['things'])

    things = client.list_things(nextToken=things['nextToken'], attributeName='foo', attributeValue='bar')
    things.should_not.have.key('nextToken')
    things.should.have.key('things').which.should.have.length_of(16)
    things['things'][0]['thingName'].should.equal('153')
    things['things'][0]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/153')
    things['things'][-1]['thingName'].should.equal('198')
    things['things'][-1]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/198')
    all(item['attributes'] == {'foo': 'bar'} for item in things['things'])

    # Test filter for attributes and thingTypeName
    things = client.list_things(thingTypeName=thing_type_name, attributeName='foo', attributeValue='bar')
    things.should_not.have.key('nextToken')
    things.should.have.key('things').which.should.have.length_of(33)
    things['things'][0]['thingName'].should.equal('6')
    things['things'][0]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/6')
    things['things'][-1]['thingName'].should.equal('198')
    things['things'][-1]['thingArn'].should.equal('arn:aws:iot:ap-northeast-1:1:thing/198')
    all(item['attributes'] == {'foo': 'bar'} and item['thingTypeName'] == thing_type_name for item in things['things'])


@mock_iot
def test_certs():
    client = boto3.client('iot', region_name='us-east-1')
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert.should.have.key('certificateArn').which.should_not.be.none
    cert.should.have.key('certificateId').which.should_not.be.none
    cert.should.have.key('certificatePem').which.should_not.be.none
    cert.should.have.key('keyPair')
    cert['keyPair'].should.have.key('PublicKey').which.should_not.be.none
    cert['keyPair'].should.have.key('PrivateKey').which.should_not.be.none
    cert_id = cert['certificateId']

    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key('certificateDescription')
    cert_desc = cert['certificateDescription']
    cert_desc.should.have.key('certificateArn').which.should_not.be.none
    cert_desc.should.have.key('certificateId').which.should_not.be.none
    cert_desc.should.have.key('certificatePem').which.should_not.be.none
    cert_desc.should.have.key('status').which.should.equal('ACTIVE')
    cert_pem = cert_desc['certificatePem']

    res = client.list_certificates()
    for cert in res['certificates']:
        cert.should.have.key('certificateArn').which.should_not.be.none
        cert.should.have.key('certificateId').which.should_not.be.none
        cert.should.have.key('status').which.should_not.be.none
        cert.should.have.key('creationDate').which.should_not.be.none

    client.update_certificate(certificateId=cert_id, newStatus='REVOKED')
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert['certificateDescription']
    cert_desc.should.have.key('status').which.should.equal('REVOKED')

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key('certificates')

    # Test register_certificate flow
    cert = client.register_certificate(certificatePem=cert_pem, setAsActive=True)
    cert.should.have.key('certificateId').which.should_not.be.none
    cert.should.have.key('certificateArn').which.should_not.be.none
    cert_id = cert['certificateId']

    res = client.list_certificates()
    res.should.have.key('certificates').which.should.have.length_of(1)
    for cert in res['certificates']:
        cert.should.have.key('certificateArn').which.should_not.be.none
        cert.should.have.key('certificateId').which.should_not.be.none
        cert.should.have.key('status').which.should_not.be.none
        cert.should.have.key('creationDate').which.should_not.be.none

    client.update_certificate(certificateId=cert_id, newStatus='REVOKED')
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert['certificateDescription']
    cert_desc.should.have.key('status').which.should.equal('REVOKED')

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key('certificates')


@mock_iot
def test_delete_policy_validation():
    doc = """{
    "Version": "2012-10-17",
    "Statement":[
        {
            "Effect":"Allow",
            "Action":[
                "iot: *"
            ],
            "Resource":"*"
        }
      ]
    }
    """
    client = boto3.client('iot', region_name='ap-northeast-1')
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert['certificateArn']
    policy_name = 'my-policy'
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_principal_policy(policyName=policy_name, principal=cert_arn)

    with assert_raises(ClientError) as e:
        client.delete_policy(policyName=policy_name)
    e.exception.response['Error']['Message'].should.contain(
        'The policy cannot be deleted as the policy is attached to one or more principals (name=%s)' % policy_name)
    res = client.list_policies()
    res.should.have.key('policies').which.should.have.length_of(1)

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    client.delete_policy(policyName=policy_name)
    res = client.list_policies()
    res.should.have.key('policies').which.should.have.length_of(0)


@mock_iot
def test_delete_certificate_validation():
    doc = """{
    "Version": "2012-10-17",
    "Statement":[
        {
            "Effect":"Allow",
            "Action":[
                "iot: *"
            ],
            "Resource":"*"
        }
      ]
    }
    """
    client = boto3.client('iot', region_name='ap-northeast-1')
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_id = cert['certificateId']
    cert_arn = cert['certificateArn']
    policy_name = 'my-policy'
    thing_name = 'thing-1'
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_principal_policy(policyName=policy_name, principal=cert_arn)
    client.create_thing(thingName=thing_name)
    client.attach_thing_principal(thingName=thing_name, principal=cert_arn)

    with assert_raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    e.exception.response['Error']['Message'].should.contain(
        'Certificate must be deactivated (not ACTIVE) before deletion.')
    res = client.list_certificates()
    res.should.have.key('certificates').which.should.have.length_of(1)

    client.update_certificate(certificateId=cert_id, newStatus='REVOKED')
    with assert_raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    e.exception.response['Error']['Message'].should.contain(
        'Things must be detached before deletion (arn: %s)' % cert_arn)
    res = client.list_certificates()
    res.should.have.key('certificates').which.should.have.length_of(1)

    client.detach_thing_principal(thingName=thing_name, principal=cert_arn)
    with assert_raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    e.exception.response['Error']['Message'].should.contain(
        'Certificate policies must be detached before deletion (arn: %s)' % cert_arn)
    res = client.list_certificates()
    res.should.have.key('certificates').which.should.have.length_of(1)

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key('certificates').which.should.have.length_of(0)


@mock_iot
def test_certs_create_inactive():
    client = boto3.client('iot', region_name='ap-northeast-1')
    cert = client.create_keys_and_certificate(setAsActive=False)
    cert_id = cert['certificateId']

    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key('certificateDescription')
    cert_desc = cert['certificateDescription']
    cert_desc.should.have.key('status').which.should.equal('INACTIVE')

    client.update_certificate(certificateId=cert_id, newStatus='ACTIVE')
    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key('certificateDescription')
    cert_desc = cert['certificateDescription']
    cert_desc.should.have.key('status').which.should.equal('ACTIVE')


@mock_iot
def test_policy():
    client = boto3.client('iot', region_name='ap-northeast-1')
    name = 'my-policy'
    doc = '{}'
    policy = client.create_policy(policyName=name, policyDocument=doc)
    policy.should.have.key('policyName').which.should.equal(name)
    policy.should.have.key('policyArn').which.should_not.be.none
    policy.should.have.key('policyDocument').which.should.equal(doc)
    policy.should.have.key('policyVersionId').which.should.equal('1')

    policy = client.get_policy(policyName=name)
    policy.should.have.key('policyName').which.should.equal(name)
    policy.should.have.key('policyArn').which.should_not.be.none
    policy.should.have.key('policyDocument').which.should.equal(doc)
    policy.should.have.key('defaultVersionId').which.should.equal('1')

    res = client.list_policies()
    res.should.have.key('policies').which.should.have.length_of(1)
    for policy in res['policies']:
        policy.should.have.key('policyName').which.should_not.be.none
        policy.should.have.key('policyArn').which.should_not.be.none

    client.delete_policy(policyName=name)
    res = client.list_policies()
    res.should.have.key('policies').which.should.have.length_of(0)


@mock_iot
def test_principal_policy():
    client = boto3.client('iot', region_name='ap-northeast-1')
    policy_name = 'my-policy'
    doc = '{}'
    client.create_policy(policyName=policy_name, policyDocument=doc)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert['certificateArn']

    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key('policies').which.should.have.length_of(1)
    for policy in res['policies']:
        policy.should.have.key('policyName').which.should_not.be.none
        policy.should.have.key('policyArn').which.should_not.be.none

    # do nothing if policy have already attached to certificate
    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key('policies').which.should.have.length_of(1)
    for policy in res['policies']:
        policy.should.have.key('policyName').which.should_not.be.none
        policy.should.have.key('policyArn').which.should_not.be.none

    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key('principals').which.should.have.length_of(1)
    for principal in res['principals']:
        principal.should_not.be.none

    client.detach_policy(policyName=policy_name, target=cert_arn)
    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key('policies').which.should.have.length_of(0)
    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key('principals').which.should.have.length_of(0)
    with assert_raises(ClientError) as e:
        client.detach_policy(policyName=policy_name, target=cert_arn)
    e.exception.response['Error']['Code'].should.equal('ResourceNotFoundException')


@mock_iot
def test_principal_policy_deprecated():
    client = boto3.client('iot', region_name='ap-northeast-1')
    policy_name = 'my-policy'
    doc = '{}'
    policy = client.create_policy(policyName=policy_name, policyDocument=doc)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert['certificateArn']

    client.attach_principal_policy(policyName=policy_name, principal=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key('policies').which.should.have.length_of(1)
    for policy in res['policies']:
        policy.should.have.key('policyName').which.should_not.be.none
        policy.should.have.key('policyArn').which.should_not.be.none

    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key('principals').which.should.have.length_of(1)
    for principal in res['principals']:
        principal.should_not.be.none

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key('policies').which.should.have.length_of(0)
    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key('principals').which.should.have.length_of(0)


@mock_iot
def test_principal_thing():
    client = boto3.client('iot', region_name='ap-northeast-1')
    thing_name = 'my-thing'
    thing = client.create_thing(thingName=thing_name)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert['certificateArn']

    client.attach_thing_principal(thingName=thing_name, principal=cert_arn)

    res = client.list_principal_things(principal=cert_arn)
    res.should.have.key('things').which.should.have.length_of(1)
    for thing in res['things']:
        thing.should_not.be.none
    res = client.list_thing_principals(thingName=thing_name)
    res.should.have.key('principals').which.should.have.length_of(1)
    for principal in res['principals']:
        principal.should_not.be.none

    client.detach_thing_principal(thingName=thing_name, principal=cert_arn)
    res = client.list_principal_things(principal=cert_arn)
    res.should.have.key('things').which.should.have.length_of(0)
    res = client.list_thing_principals(thingName=thing_name)
    res.should.have.key('principals').which.should.have.length_of(0)


@mock_iot
def test_thing_groups():
    client = boto3.client('iot', region_name='ap-northeast-1')
    group_name = 'my-group-name'

    # thing group
    thing_group = client.create_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupName').which.should.equal(group_name)
    thing_group.should.have.key('thingGroupArn')

    res = client.list_thing_groups()
    res.should.have.key('thingGroups').which.should.have.length_of(1)
    for thing_group in res['thingGroups']:
        thing_group.should.have.key('groupName').which.should_not.be.none
        thing_group.should.have.key('groupArn').which.should_not.be.none

    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupName').which.should.equal(group_name)
    thing_group.should.have.key('thingGroupProperties')
    thing_group.should.have.key('thingGroupMetadata')
    thing_group.should.have.key('version')

    # delete thing group
    client.delete_thing_group(thingGroupName=group_name)
    res = client.list_thing_groups()
    res.should.have.key('thingGroups').which.should.have.length_of(0)

    # props create test
    props = {
        'thingGroupDescription': 'my first thing group',
        'attributePayload': {
            'attributes': {
                'key1': 'val01',
                'Key02': 'VAL2'
            }
        }
    }
    thing_group = client.create_thing_group(thingGroupName=group_name, thingGroupProperties=props)
    thing_group.should.have.key('thingGroupName').which.should.equal(group_name)
    thing_group.should.have.key('thingGroupArn')

    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupProperties') \
        .which.should.have.key('attributePayload') \
        .which.should.have.key('attributes')
    res_props = thing_group['thingGroupProperties']['attributePayload']['attributes']
    res_props.should.have.key('key1').which.should.equal('val01')
    res_props.should.have.key('Key02').which.should.equal('VAL2')

    # props update test with merge
    new_props = {
        'attributePayload': {
            'attributes': {
                'k3': 'v3'
            },
            'merge': True
        }
    }
    client.update_thing_group(
        thingGroupName=group_name,
        thingGroupProperties=new_props
    )
    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupProperties') \
        .which.should.have.key('attributePayload') \
        .which.should.have.key('attributes')
    res_props = thing_group['thingGroupProperties']['attributePayload']['attributes']
    res_props.should.have.key('key1').which.should.equal('val01')
    res_props.should.have.key('Key02').which.should.equal('VAL2')

    res_props.should.have.key('k3').which.should.equal('v3')

    # props update test
    new_props = {
        'attributePayload': {
            'attributes': {
                'k4': 'v4'
            }
        }
    }
    client.update_thing_group(
        thingGroupName=group_name,
        thingGroupProperties=new_props
    )
    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupProperties') \
        .which.should.have.key('attributePayload') \
        .which.should.have.key('attributes')
    res_props = thing_group['thingGroupProperties']['attributePayload']['attributes']
    res_props.should.have.key('k4').which.should.equal('v4')
    res_props.should_not.have.key('key1')


@mock_iot
def test_thing_group_relations():
    client = boto3.client('iot', region_name='ap-northeast-1')
    name = 'my-thing'
    group_name = 'my-group-name'

    # thing group
    thing_group = client.create_thing_group(thingGroupName=group_name)
    thing_group.should.have.key('thingGroupName').which.should.equal(group_name)
    thing_group.should.have.key('thingGroupArn')

    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')

    # add in 4 way
    client.add_thing_to_thing_group(
        thingGroupName=group_name,
        thingName=name
    )
    client.add_thing_to_thing_group(
        thingGroupArn=thing_group['thingGroupArn'],
        thingArn=thing['thingArn']
    )
    client.add_thing_to_thing_group(
        thingGroupName=group_name,
        thingArn=thing['thingArn']
    )
    client.add_thing_to_thing_group(
        thingGroupArn=thing_group['thingGroupArn'],
        thingName=name
    )

    things = client.list_things_in_thing_group(
        thingGroupName=group_name
    )
    things.should.have.key('things')
    things['things'].should.have.length_of(1)

    thing_groups = client.list_thing_groups_for_thing(
        thingName=name
    )
    thing_groups.should.have.key('thingGroups')
    thing_groups['thingGroups'].should.have.length_of(1)

    # remove in 4 way
    client.remove_thing_from_thing_group(
        thingGroupName=group_name,
        thingName=name
    )
    client.remove_thing_from_thing_group(
        thingGroupArn=thing_group['thingGroupArn'],
        thingArn=thing['thingArn']
    )
    client.remove_thing_from_thing_group(
        thingGroupName=group_name,
        thingArn=thing['thingArn']
    )
    client.remove_thing_from_thing_group(
        thingGroupArn=thing_group['thingGroupArn'],
        thingName=name
    )
    things = client.list_things_in_thing_group(
        thingGroupName=group_name
    )
    things.should.have.key('things')
    things['things'].should.have.length_of(0)

    # update thing group for thing
    client.update_thing_groups_for_thing(
        thingName=name,
        thingGroupsToAdd=[
            group_name
        ]
    )
    things = client.list_things_in_thing_group(
        thingGroupName=group_name
    )
    things.should.have.key('things')
    things['things'].should.have.length_of(1)

    client.update_thing_groups_for_thing(
        thingName=name,
        thingGroupsToRemove=[
            group_name
        ]
    )
    things = client.list_things_in_thing_group(
        thingGroupName=group_name
    )
    things.should.have.key('things')
    things['things'].should.have.length_of(0)


@mock_iot
def test_create_job():
    client = boto3.client('iot', region_name='eu-west-1')
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')

    # job document
    job_document = {
        "field": "value"
    }

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            'roleArn': 'arn:aws:iam::1:role/service-role/iot_job_role',
            'expiresInSec': 123
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={
            'maximumPerMinute': 10
        }
    )

    job.should.have.key('jobId').which.should.equal(job_id)
    job.should.have.key('jobArn')
    job.should.have.key('description')


@mock_iot
def test_describe_job():
    client = boto3.client('iot', region_name='eu-west-1')
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        documentSource="https://s3-eu-west-1.amazonaws.com/bucket-name/job_document.json",
        presignedUrlConfig={
            'roleArn': 'arn:aws:iam::1:role/service-role/iot_job_role',
            'expiresInSec': 123
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={
            'maximumPerMinute': 10
        }
    )

    job.should.have.key('jobId').which.should.equal(job_id)
    job.should.have.key('jobArn')

    job = client.describe_job(jobId=job_id)
    job.should.have.key('documentSource')
    job.should.have.key('job')
    job.should.have.key('job').which.should.have.key("jobArn")
    job.should.have.key('job').which.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key('job').which.should.have.key("targets")
    job.should.have.key('job').which.should.have.key("jobProcessDetails")
    job.should.have.key('job').which.should.have.key("lastUpdatedAt")
    job.should.have.key('job').which.should.have.key("createdAt")
    job.should.have.key('job').which.should.have.key("jobExecutionsRolloutConfig")
    job.should.have.key('job').which.should.have.key("targetSelection").which.should.equal("CONTINUOUS")
    job.should.have.key('job').which.should.have.key("presignedUrlConfig")
    job.should.have.key('job').which.should.have.key("presignedUrlConfig").which.should.have.key(
        "roleArn").which.should.equal('arn:aws:iam::1:role/service-role/iot_job_role')
    job.should.have.key('job').which.should.have.key("presignedUrlConfig").which.should.have.key(
        "expiresInSec").which.should.equal(123)
    job.should.have.key('job').which.should.have.key("jobExecutionsRolloutConfig").which.should.have.key(
        "maximumPerMinute").which.should.equal(10)


@mock_iot
def test_describe_job_1():
    client = boto3.client('iot', region_name='eu-west-1')
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')

    # job document
    job_document = {
        "field": "value"
    }

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        presignedUrlConfig={
            'roleArn': 'arn:aws:iam::1:role/service-role/iot_job_role',
            'expiresInSec': 123
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={
            'maximumPerMinute': 10
        }
    )

    job.should.have.key('jobId').which.should.equal(job_id)
    job.should.have.key('jobArn')

    job = client.describe_job(jobId=job_id)
    job.should.have.key('job')
    job.should.have.key('job').which.should.have.key("jobArn")
    job.should.have.key('job').which.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key('job').which.should.have.key("targets")
    job.should.have.key('job').which.should.have.key("jobProcessDetails")
    job.should.have.key('job').which.should.have.key("lastUpdatedAt")
    job.should.have.key('job').which.should.have.key("createdAt")
    job.should.have.key('job').which.should.have.key("jobExecutionsRolloutConfig")
    job.should.have.key('job').which.should.have.key("targetSelection").which.should.equal("CONTINUOUS")
    job.should.have.key('job').which.should.have.key("presignedUrlConfig")
    job.should.have.key('job').which.should.have.key("presignedUrlConfig").which.should.have.key(
        "roleArn").which.should.equal('arn:aws:iam::1:role/service-role/iot_job_role')
    job.should.have.key('job').which.should.have.key("presignedUrlConfig").which.should.have.key(
        "expiresInSec").which.should.equal(123)
    job.should.have.key('job').which.should.have.key("jobExecutionsRolloutConfig").which.should.have.key(
        "maximumPerMinute").which.should.equal(10)
