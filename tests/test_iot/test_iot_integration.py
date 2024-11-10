import json

import boto3

from moto import mock_aws


@mock_aws
def test_search_things_include_named_shadow():
    iot_client = boto3.client("iot", region_name="ap-northeast-1")
    iotdata_client = boto3.client("iot-data", region_name="ap-northeast-1")
    raw_payload = b'{"state": {"desired": {"led": "on"}, "reported": {"led": "off"}}}'

    thing_name = "test-thing-name"
    iot_client.create_thing(thingName=thing_name)
    iotdata_client.update_thing_shadow(
        thingName=thing_name, shadowName="test_shadow", payload=raw_payload
    )

    resp = iot_client.search_index(queryString=f"thingName:{thing_name}")

    assert len(resp["things"]) == 1
    shadow = json.loads(resp["things"][0]["shadow"])

    assert shadow["name"]["test_shadow"]["desired"] == {"led": "on"}
    assert shadow["name"]["test_shadow"]["reported"] == {"led": "off"}
    assert shadow["name"]["test_shadow"]["hasDelta"]
