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

    thing_types = client.list_thing_types()
    thing_types.should.have.key('thingTypes').which.should.have.length_of(1)
    for thing_type in thing_types['thingTypes']:
        thing_type.should.have.key('thingTypeName').which.should_not.be.none

    thing_type = client.describe_thing_type(thingTypeName=type_name)
    thing_type.should.have.key('thingTypeName').which.should.equal(type_name)
    thing_type.should.have.key('thingTypeProperties')
    thing_type.should.have.key('thingTypeMetadata')

    # thing
    thing = client.create_thing(thingName=name, thingTypeName=type_name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('thingArn')
    things = client.list_things()
    things.should.have.key('things').which.should.have.length_of(1)
    for thing in things['things']:
        thing.should.have.key('thingName').which.should_not.be.none

    thing = client.update_thing(thingName=name, attributePayload={'attributes': {'k1': 'v1'}})
    things = client.list_things()
    things.should.have.key('things').which.should.have.length_of(1)
    for thing in things['things']:
        thing.should.have.key('thingName').which.should_not.be.none
    things['things'][0]['attributes'].should.have.key('k1').which.should.equal('v1')

    thing = client.describe_thing(thingName=name)
    thing.should.have.key('thingName').which.should.equal(name)
    thing.should.have.key('defaultClientId')
    thing.should.have.key('thingTypeName')
    thing.should.have.key('attributes')
    thing.should.have.key('version')

    # delete thing
    client.delete_thing(thingName=name)
    things = client.list_things()
    things.should.have.key('things').which.should.have.length_of(0)

    # delete thing type
    client.delete_thing_type(thingTypeName=type_name)
    thing_types = client.list_thing_types()
    thing_types.should.have.key('thingTypes').which.should.have.length_of(0)


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

    certs = client.list_certificates()
    certs.should.have.key('certificates').which.should.have.length_of(1)
    for cert in certs['certificates']:
        cert.should.have.key('certificateArn').which.should_not.be.none
        cert.should.have.key('certificateId').which.should_not.be.none
        cert.should.have.key('status').which.should_not.be.none
        cert.should.have.key('creationDate').which.should_not.be.none

    client.update_certificate(certificateId=cert_id, newStatus='REVOKED')
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc.should.have.key('status').which.should.equal('ACTIVE')

    client.delete_certificate(certificateId=cert_id)
    certs = client.list_certificates()
    certs.should.have.key('certificates').which.should.have.length_of(0)
