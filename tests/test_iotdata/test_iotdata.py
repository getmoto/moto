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
        # Boolean flip
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
        # No data
        ({}, {}, {"reported": {"online": False}}, {"reported": {"online": False}}),
        # Missing data
        ({}, {}, {"reported": {"online": None}}, {}),
        (
            {"desired": {}},
            {},
            {"reported": {"online": False}},
            {"reported": {"online": False}},
        ),
        # Missing key
        (
            {"desired": {"enabled": True}},
            {"desired": {"enabled": True}, "delta": {"enabled": True}},
            {"reported": {}},
            {"desired": {"enabled": True}, "delta": {"enabled": True}},
        ),
        # Changed key
        (
            {"desired": {"enabled": True}},
            {"desired": {"enabled": True}, "delta": {"enabled": True}},
            {"reported": {"online": True}},
            {
                "desired": {"enabled": True},
                "reported": {"online": True},
                "delta": {"enabled": True},
            },
        ),
        # Remove from list
        (
            {"reported": {"list": ["value_1", "value_2"]}},
            {"reported": {"list": ["value_1", "value_2"]}},
            {"desired": {"list": ["value_1"]}},
            {
                "desired": {"list": ["value_1"]},
                "reported": {"list": ["value_1", "value_2"]},
                "delta": {"list": ["value_1"]},
            },
        ),
        # Remove And Update from list
        (
            {"reported": {"list": ["value_1", "value_2"]}},
            {"reported": {"list": ["value_1", "value_2"]}},
            {"desired": {"list": ["value_1", "value_3"]}},
            {
                "desired": {"list": ["value_1", "value_3"]},
                "reported": {"list": ["value_1", "value_2"]},
                "delta": {"list": ["value_1", "value_3"]},
            },
        ),
        # Remove from nested lists
        (
            {"reported": {"list": [["value_1"], ["value_2"]]}},
            {"reported": {"list": [["value_1"], ["value_2"]]}},
            {"desired": {"list": [["value_1"]]}},
            {
                "desired": {"list": [["value_1"]]},
                "reported": {"list": [["value_1"], ["value_2"]]},
                "delta": {"list": [["value_1"]]},
            },
        ),
        # Append to nested list
        (
            {"reported": {"a": {"b": ["d"]}}},
            {"reported": {"a": {"b": ["d"]}}},
            {"desired": {"a": {"b": ["c", "d"]}}},
            {
                "delta": {"a": {"b": ["c", "d"]}},
                "desired": {"a": {"b": ["c", "d"]}},
                "reported": {"a": {"b": ["d"]}},
            },
        ),
        # Update nested dict
        (
            {"reported": {"a": {"b": {"c": "d", "e": "f"}}}},
            {"reported": {"a": {"b": {"c": "d", "e": "f"}}}},
            {"desired": {"a": {"b": {"c": "d2"}}}},
            {
                "delta": {"a": {"b": {"c": "d2"}}},
                "desired": {"a": {"b": {"c": "d2"}}},
                "reported": {"a": {"b": {"c": "d", "e": "f"}}},
            },
        ),
        (
            {"reported": {"a1": {"b1": {"c": "d"}}}},
            {"reported": {"a1": {"b1": {"c": "d"}}}},
            {"desired": {"a1": {"b1": {"c": "d"}}, "a2": {"b2": "sth"}}},
            {
                "delta": {"a2": {"b2": "sth"}},
                "desired": {"a1": {"b1": {"c": "d"}}, "a2": {"b2": "sth"}},
                "reported": {"a1": {"b1": {"c": "d"}}},
            },
        ),
        (
            {"reported": {"a": {"b1": {"c": "d"}}}},
            {"reported": {"a": {"b1": {"c": "d"}}}},
            {"desired": {"a": {"b1": {"c": "d"}, "b2": "sth"}}},
            {
                "delta": {"a": {"b2": "sth"}},
                "desired": {"a": {"b1": {"c": "d"}, "b2": "sth"}},
                "reported": {"a": {"b1": {"c": "d"}}},
            },
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


@iot_aws_verified()
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "initial_state,updated_state",
    [
        # Insert new dicts
        (
            {"a": 1, "b": {"c": 3}},
            {"a": 1, "b": {"c": 3}, "d": {}},
        ),
        # Update existing value with new dicts
        (
            {"a": 1, "b": {"c": 3}, "d": {}},
            {"a": 1, "b": {"c": {}}, "d": {}},
        ),
        # Update existing value with full dicts
        (
            {"a": 1, "b": {"c": 3}},
            {"a": 1, "b": {"c": {"d": 3}}},
        ),
    ],
)
def test_update_desired(
    initial_state: dict[str, str],
    updated_state: dict[str, str],
    name: Optional[str] = None,
) -> None:
    client = boto3.client("iot-data", region_name="ap-northeast-1")

    # CREATE
    payload = json.dumps({"state": {"desired": initial_state}}).encode("utf-8")
    client.update_thing_shadow(thingName=name, payload=payload)

    # UPDATE
    payload = json.dumps({"state": {"desired": updated_state}}).encode("utf-8")
    client.update_thing_shadow(thingName=name, payload=payload)

    # GET --> Verify the updated state is returned as-is
    res = client.get_thing_shadow(thingName=name)
    result_payload = json.loads(res["payload"].read())

    assert result_payload["state"]["delta"] == updated_state
    assert result_payload["state"]["desired"] == updated_state
