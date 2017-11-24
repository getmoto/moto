from __future__ import unicode_literals

import json
import boto3
import sure  # noqa
from nose.tools import assert_raises
from botocore.exceptions import ClientError
from moto import mock_iotdata, mock_iot


@mock_iot
@mock_iotdata
def test_basic():
    iot_client = boto3.client('iot', region_name='ap-northeast-1')
    client = boto3.client('iot-data', region_name='ap-northeast-1')
    name = 'my-thing'
    raw_payload = b'{"state": {"desired": {"led": "on"}}}'
    iot_client.create_thing(thingName=name)

    with assert_raises(ClientError):
        client.get_thing_shadow(thingName=name)

    res = client.update_thing_shadow(thingName=name, payload=raw_payload)

    payload = json.loads(res['payload'].read())
    expected_state = '{"desired": {"led": "on"}}'
    payload.should.have.key('state').which.should.equal(json.loads(expected_state))
    payload.should.have.key('metadata').which.should.have.key('desired').which.should.have.key('led')
    payload.should.have.key('version').which.should.equal(1)
    payload.should.have.key('timestamp')

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res['payload'].read())
    expected_state = b'{"desired": {"led": "on"}, "delta": {"led": "on"}}'
    payload.should.have.key('state').which.should.equal(json.loads(expected_state))
    payload.should.have.key('metadata').which.should.have.key('desired').which.should.have.key('led')
    payload.should.have.key('version').which.should.equal(1)
    payload.should.have.key('timestamp')

    client.delete_thing_shadow(thingName=name)
    with assert_raises(ClientError):
        client.get_thing_shadow(thingName=name)


@mock_iot
@mock_iotdata
def test_update():
    iot_client = boto3.client('iot', region_name='ap-northeast-1')
    client = boto3.client('iot-data', region_name='ap-northeast-1')
    name = 'my-thing'
    raw_payload = b'{"state": {"desired": {"led": "on"}}}'
    iot_client.create_thing(thingName=name)

    # first update
    res = client.update_thing_shadow(thingName=name, payload=raw_payload)
    payload = json.loads(res['payload'].read())
    expected_state = '{"desired": {"led": "on"}}'
    payload.should.have.key('state').which.should.equal(json.loads(expected_state))
    payload.should.have.key('metadata').which.should.have.key('desired').which.should.have.key('led')
    payload.should.have.key('version').which.should.equal(1)
    payload.should.have.key('timestamp')

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res['payload'].read())
    expected_state = b'{"desired": {"led": "on"}, "delta": {"led": "on"}}'
    payload.should.have.key('state').which.should.equal(json.loads(expected_state))
    payload.should.have.key('metadata').which.should.have.key('desired').which.should.have.key('led')
    payload.should.have.key('version').which.should.equal(1)
    payload.should.have.key('timestamp')

    # reporting new state
    new_payload = b'{"state": {"reported": {"led": "on"}}}'
    res = client.update_thing_shadow(thingName=name, payload=new_payload)
    payload = json.loads(res['payload'].read())
    expected_state = '{"reported": {"led": "on"}}'
    payload.should.have.key('state').which.should.equal(json.loads(expected_state))
    payload.should.have.key('metadata').which.should.have.key('reported').which.should.have.key('led')
    payload.should.have.key('version').which.should.equal(2)
    payload.should.have.key('timestamp')

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res['payload'].read())
    expected_state = b'{"desired": {"led": "on"}, "reported": {"led": "on"}}'
    payload.should.have.key('state').which.should.equal(json.loads(expected_state))
    payload.should.have.key('metadata').which.should.have.key('desired').which.should.have.key('led')
    payload.should.have.key('version').which.should.equal(2)
    payload.should.have.key('timestamp')


@mock_iotdata
def test_publish():
    client = boto3.client('iot-data', region_name='ap-northeast-1')
    client.publish(topic='test/topic', qos=1, payload=b'')
