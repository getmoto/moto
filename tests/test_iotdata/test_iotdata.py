from __future__ import unicode_literals

import json
import boto3
import sure  # noqa
import pytest
from botocore.exceptions import ClientError
from moto import mock_iotdata, mock_iot


@mock_iot
@mock_iotdata
def test_basic():
    iot_client = boto3.client("iot", region_name="ap-northeast-1")
    client = boto3.client("iot-data", region_name="ap-northeast-1")
    name = "my-thing"
    raw_payload = b'{"state": {"desired": {"led": "on"}}}'
    iot_client.create_thing(thingName=name)

    with pytest.raises(ClientError):
        client.get_thing_shadow(thingName=name)

    res = client.update_thing_shadow(thingName=name, payload=raw_payload)

    payload = json.loads(res["payload"].read())
    expected_state = '{"desired": {"led": "on"}}'
    payload.should.have.key("state").which.should.equal(json.loads(expected_state))
    payload.should.have.key("metadata").which.should.have.key(
        "desired"
    ).which.should.have.key("led")
    payload.should.have.key("version").which.should.equal(1)
    payload.should.have.key("timestamp")

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res["payload"].read())
    expected_state = b'{"desired": {"led": "on"}, "delta": {"led": "on"}}'
    payload.should.have.key("state").which.should.equal(json.loads(expected_state))
    payload.should.have.key("metadata").which.should.have.key(
        "desired"
    ).which.should.have.key("led")
    payload.should.have.key("version").which.should.equal(1)
    payload.should.have.key("timestamp")

    client.delete_thing_shadow(thingName=name)
    with pytest.raises(ClientError):
        client.get_thing_shadow(thingName=name)


@mock_iot
@mock_iotdata
def test_update():
    iot_client = boto3.client("iot", region_name="ap-northeast-1")
    client = boto3.client("iot-data", region_name="ap-northeast-1")
    name = "my-thing"
    raw_payload = b'{"state": {"desired": {"led": "on"}}}'
    iot_client.create_thing(thingName=name)

    # first update
    res = client.update_thing_shadow(thingName=name, payload=raw_payload)
    payload = json.loads(res["payload"].read())
    expected_state = '{"desired": {"led": "on"}}'
    payload.should.have.key("state").which.should.equal(json.loads(expected_state))
    payload.should.have.key("metadata").which.should.have.key(
        "desired"
    ).which.should.have.key("led")
    payload.should.have.key("version").which.should.equal(1)
    payload.should.have.key("timestamp")

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res["payload"].read())
    expected_state = b'{"desired": {"led": "on"}, "delta": {"led": "on"}}'
    payload.should.have.key("state").which.should.equal(json.loads(expected_state))
    payload.should.have.key("metadata").which.should.have.key(
        "desired"
    ).which.should.have.key("led")
    payload.should.have.key("version").which.should.equal(1)
    payload.should.have.key("timestamp")

    # reporting new state
    new_payload = b'{"state": {"reported": {"led": "on"}}}'
    res = client.update_thing_shadow(thingName=name, payload=new_payload)
    payload = json.loads(res["payload"].read())
    expected_state = '{"reported": {"led": "on"}}'
    payload.should.have.key("state").which.should.equal(json.loads(expected_state))
    payload.should.have.key("metadata").which.should.have.key(
        "reported"
    ).which.should.have.key("led")
    payload.should.have.key("version").which.should.equal(2)
    payload.should.have.key("timestamp")

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res["payload"].read())
    expected_state = b'{"desired": {"led": "on"}, "reported": {"led": "on"}}'
    payload.should.have.key("state").which.should.equal(json.loads(expected_state))
    payload.should.have.key("metadata").which.should.have.key(
        "desired"
    ).which.should.have.key("led")
    payload.should.have.key("version").which.should.equal(2)
    payload.should.have.key("timestamp")

    raw_payload = b'{"state": {"desired": {"led": "on"}}, "version": 1}'
    with pytest.raises(ClientError) as ex:
        client.update_thing_shadow(thingName=name, payload=raw_payload)
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(409)
    ex.value.response["Error"]["Message"].should.equal("Version conflict")


@mock_iotdata
def test_publish():
    client = boto3.client("iot-data", region_name="ap-northeast-1")
    client.publish(topic="test/topic", qos=1, payload=b"")


@mock_iot
@mock_iotdata
def test_delete_field_from_device_shadow():
    test_thing_name = "TestThing"

    iot_raw_client = boto3.client("iot", region_name="eu-central-1")
    iot_raw_client.create_thing(thingName=test_thing_name)
    iot = boto3.client("iot-data", region_name="eu-central-1")

    iot.update_thing_shadow(
        thingName=test_thing_name,
        payload=json.dumps({"state": {"desired": {"state1": 1, "state2": 2}}}),
    )
    response = json.loads(
        iot.get_thing_shadow(thingName=test_thing_name)["payload"].read()
    )
    assert len(response["state"]["desired"]) == 2

    iot.update_thing_shadow(
        thingName=test_thing_name,
        payload=json.dumps({"state": {"desired": {"state1": None}}}),
    )
    response = json.loads(
        iot.get_thing_shadow(thingName=test_thing_name)["payload"].read()
    )
    assert len(response["state"]["desired"]) == 1
    assert "state2" in response["state"]["desired"]

    iot.update_thing_shadow(
        thingName=test_thing_name,
        payload=json.dumps({"state": {"desired": {"state2": None}}}),
    )
    response = json.loads(
        iot.get_thing_shadow(thingName=test_thing_name)["payload"].read()
    )
    assert "desired" not in response["state"]
