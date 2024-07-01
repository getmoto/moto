import json
import sys
from typing import Dict, Optional
from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

import moto.iotdata.models
from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.utilities.distutils_version import LooseVersion

from . import iot_aws_verified

boto3_version = sys.modules["botocore"].__version__


@iot_aws_verified()
@pytest.mark.aws_verified
def test_basic(name: Optional[str] = None) -> None:
    client = boto3.client("iot-data", region_name="ap-northeast-1")

    raw_payload = b'{"state": {"desired": {"led": "on"}}}'

    with pytest.raises(ClientError):
        client.get_thing_shadow(thingName=name)

    res = client.update_thing_shadow(thingName=name, payload=raw_payload)

    payload = json.loads(res["payload"].read())
    expected_state = '{"desired": {"led": "on"}}'
    assert payload["state"] == json.loads(expected_state)
    assert "led" in payload["metadata"]["desired"]
    assert payload["version"] == 1
    assert "timestamp" in payload

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res["payload"].read())
    expected_state = '{"desired": {"led": "on"}, "delta": {"led": "on"}}'
    assert payload["state"] == json.loads(expected_state)
    assert "led" in payload["metadata"]["desired"]
    assert payload["version"] == 1
    assert "timestamp" in payload

    client.delete_thing_shadow(thingName=name)
    with pytest.raises(ClientError):
        client.get_thing_shadow(thingName=name)


@iot_aws_verified()
@pytest.mark.aws_verified
def test_update(name: Optional[str] = None) -> None:
    client = boto3.client("iot-data", region_name="ap-northeast-1")
    raw_payload = b'{"state": {"desired": {"led": "on"}}}'

    # first update
    res = client.update_thing_shadow(thingName=name, payload=raw_payload)
    payload = json.loads(res["payload"].read())
    expected_state = '{"desired": {"led": "on"}}'
    assert payload["state"] == json.loads(expected_state)
    assert "led" in payload["metadata"]["desired"]
    assert payload["version"] == 1
    assert "timestamp" in payload

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res["payload"].read())
    expected_state = '{"desired": {"led": "on"}, "delta": {"led": "on"}}'
    assert payload["state"] == json.loads(expected_state)
    assert "led" in payload["metadata"]["desired"]
    assert payload["version"] == 1
    assert "timestamp" in payload

    # reporting new state
    new_payload = b'{"state": {"reported": {"led": "on"}}}'
    res = client.update_thing_shadow(thingName=name, payload=new_payload)
    payload = json.loads(res["payload"].read())
    expected_state = '{"reported": {"led": "on"}}'
    assert payload["state"] == json.loads(expected_state)
    assert "led" in payload["metadata"]["reported"]
    assert payload["version"] == 2
    assert "timestamp" in payload

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res["payload"].read())
    expected_state = '{"desired": {"led": "on"}, "reported": {"led": "on"}}'
    assert payload["state"] == json.loads(expected_state)
    assert "led" in payload["metadata"]["desired"]
    assert payload["version"] == 2
    assert "timestamp" in payload

    raw_payload = b'{"state": {"desired": {"led": "on"}}, "version": 1}'
    with pytest.raises(ClientError) as ex:
        client.update_thing_shadow(thingName=name, payload=raw_payload)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 409
    assert ex.value.response["Error"]["Message"] == "Version conflict"


@iot_aws_verified()
@pytest.mark.aws_verified
def test_create_named_shadows(name: Optional[str] = None) -> None:
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Parameter only available in newer versions")
    client = boto3.client("iot-data", region_name="ap-northeast-1")
    thing_name = name

    # default shadow
    default_payload = json.dumps({"state": {"desired": {"name": "default"}}})
    res = client.update_thing_shadow(thingName=thing_name, payload=default_payload)
    payload = json.loads(res["payload"].read())
    assert payload["state"] == {"desired": {"name": "default"}}

    # Create named shadows
    for name in ["shadow1", "shadow2"]:
        named_payload = json.dumps({"state": {"reported": {"name": name}}}).encode(
            "utf-8"
        )
        client.update_thing_shadow(
            thingName=thing_name, payload=named_payload, shadowName=name
        )

        res = client.get_thing_shadow(thingName=thing_name, shadowName=name)
        payload = json.loads(res["payload"].read())
        assert payload["state"]["reported"] == {"name": name}

    # List named shadows
    shadows = client.list_named_shadows_for_thing(thingName=thing_name)["results"]
    assert len(shadows) == 2
    assert "shadow1" in shadows
    assert "shadow2" in shadows

    # Verify we can delete a named shadow
    client.delete_thing_shadow(thingName=thing_name, shadowName="shadow2")

    with pytest.raises(ClientError) as exc:
        client.get_thing_shadow(thingName=thing_name, shadowName="shadow2")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"

    # The default and other named shadow are still there
    assert "payload" in client.get_thing_shadow(thingName=thing_name)
    assert "payload" in client.get_thing_shadow(
        thingName=thing_name, shadowName="shadow1"
    )


@mock_aws
def test_publish() -> None:
    region_name = "ap-northeast-1"
    client = boto3.client("iot-data", region_name=region_name)
    client.publish(topic="test/topic1", qos=1, payload=b"pl1")
    client.publish(topic="test/topic2", qos=1, payload=b"pl2")
    client.publish(topic="test/topic3", qos=1, payload=b"\xbf")
    client.publish(topic="test/topic4", qos=1, payload="string")

    if not settings.TEST_SERVER_MODE:
        mock_backend = moto.iotdata.models.iotdata_backends[ACCOUNT_ID][region_name]
        assert len(mock_backend.published_payloads) == 4
        assert ("test/topic1", b"pl1") in mock_backend.published_payloads
        assert ("test/topic2", b"pl2") in mock_backend.published_payloads
        assert ("test/topic3", b"\xbf") in mock_backend.published_payloads
        assert ("test/topic4", b"string") in mock_backend.published_payloads


@iot_aws_verified()
@pytest.mark.aws_verified
def test_delete_field_from_device_shadow(name: Optional[str] = None) -> None:
    iot = boto3.client("iot-data", region_name="ap-northeast-1")

    iot.update_thing_shadow(
        thingName=name,
        payload=json.dumps({"state": {"desired": {"state1": 1, "state2": 2}}}),
    )
    response = json.loads(iot.get_thing_shadow(thingName=name)["payload"].read())
    assert len(response["state"]["desired"]) == 2

    iot.update_thing_shadow(
        thingName=name,
        payload=json.dumps({"state": {"desired": {"state1": None}}}),
    )
    response = json.loads(iot.get_thing_shadow(thingName=name)["payload"].read())
    assert len(response["state"]["desired"]) == 1
    assert "state2" in response["state"]["desired"]

    iot.update_thing_shadow(
        thingName=name,
        payload=json.dumps({"state": {"desired": {"state2": None}}}),
    )
    response = json.loads(iot.get_thing_shadow(thingName=name)["payload"].read())
    assert "desired" not in response["state"]


@iot_aws_verified()
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "desired,initial_delta,reported,delta_after_report",
    [
        (
            {"desired": {"online": True}},
            {"desired": {"online": True}, "delta": {"online": True}},
            {"reported": {"online": False}},
            {
                "desired": {"online": True},
                "reported": {"online": False},
                "delta": {"online": True},
            },
        ),
        (
            {"desired": {"enabled": True}},
            {"desired": {"enabled": True}, "delta": {"enabled": True}},
            {"reported": {"online": False, "enabled": True}},
            {
                "desired": {"enabled": True},
                "reported": {"online": False, "enabled": True},
            },
        ),
        ({}, {}, {"reported": {"online": False}}, {"reported": {"online": False}}),
        ({}, {}, {"reported": {"online": None}}, {}),
        (
            {"desired": {}},
            {},
            {"reported": {"online": False}},
            {"reported": {"online": False}},
        ),
    ],
)
def test_delta_calculation(
    desired: Dict[str, Dict[str, Optional[bool]]],
    initial_delta: Dict[str, Dict[str, Optional[bool]]],
    reported: Dict[str, Dict[str, Optional[bool]]],
    delta_after_report: Dict[str, Dict[str, Optional[bool]]],
    name: Optional[str] = None,
) -> None:
    client = boto3.client("iot-data", region_name="ap-northeast-1")
    desired_payload = json.dumps({"state": desired}).encode("utf-8")
    client.update_thing_shadow(thingName=name, payload=desired_payload)

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res["payload"].read())
    assert payload["state"] == initial_delta

    reported_payload = json.dumps({"state": reported}).encode("utf-8")
    client.update_thing_shadow(thingName=name, payload=reported_payload)

    res = client.get_thing_shadow(thingName=name)
    payload = json.loads(res["payload"].read())
    assert payload["state"] == delta_after_report
