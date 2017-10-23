from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_iot


@mock_iot
def test_things():
    client = boto3.client('iot')
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

    thing = client.update_thing(thingName=name, attributePayload={'attributes': {'k1': 'v1'}})
    res = client.list_things()
    res.should.have.key('things').which.should.have.length_of(1)
    for thing in res['things']:
        thing.should.have.key('thingName').which.should_not.be.none
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
def test_certs():
    client = boto3.client('iot')
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

    res = client.list_certificates()
    res.should.have.key('certificates').which.should.have.length_of(1)
    for cert in res['certificates']:
        cert.should.have.key('certificateArn').which.should_not.be.none
        cert.should.have.key('certificateId').which.should_not.be.none
        cert.should.have.key('status').which.should_not.be.none
        cert.should.have.key('creationDate').which.should_not.be.none

    client.update_certificate(certificateId=cert_id, newStatus='REVOKED')
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc.should.have.key('status').which.should.equal('ACTIVE')

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key('certificates').which.should.have.length_of(0)

@mock_iot
def test_policy():
    client = boto3.client('iot')
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
