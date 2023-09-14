import boto3
import pytest

from moto import mock_iot


@mock_iot
@pytest.mark.parametrize(
    "query_string,results",
    [
        ["abc", {"abc", "abcefg", "uuuabc"}],
        ["thingName:abc", {"abc"}],
        ["thingName:ab*", {"abc", "abd", "abcefg"}],
        ["thingName:ab?", {"abc", "abd"}],
        ["*", {"abc", "abd", "bbe", "abcefg", "uuuabc", "bbefg"}],
    ],
)
def test_search_things(query_string, results):
    client = boto3.client("iot", region_name="ap-northeast-1")

    for name in ["abc", "abd", "bbe", "abcefg", "uuuabc", "bbefg"]:
        client.create_thing(thingName=name)

    resp = client.search_index(queryString=query_string)
    assert resp["thingGroups"] == []
    assert len(resp["things"]) == len(results)

    thing_names = [t["thingName"] for t in resp["things"]]
    assert set(thing_names) == results

    for thing in resp["things"]:
        del thing["connectivity"]["timestamp"]
        assert thing["connectivity"] == {"connected": True}


@mock_iot
@pytest.mark.parametrize(
    "query_string,results",
    [["attributes.attr0:abc", {"abc"}], ["attributes.attr1:abc", set()]],
)
def test_search_attribute_specific_value(query_string, results):
    client = boto3.client("iot", region_name="ap-northeast-1")

    for idx, name in enumerate(["abc", "abd", "bbe", "abcefg", "uuuabc", "bbefg"]):
        client.create_thing(
            thingName=name, attributePayload={"attributes": {f"attr{idx}": name}}
        )

    resp = client.search_index(queryString=query_string)
    assert resp["thingGroups"] == []
    assert len(resp["things"]) == len(results)

    thing_names = [t["thingName"] for t in resp["things"]]
    assert set(thing_names) == results
