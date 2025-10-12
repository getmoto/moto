import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@pytest.mark.parametrize(
    "query_string,results",
    [
        ["abc", {"abc", "abcefg", "uuuabc"}],
        ["thingName:abc", {"abc"}],
        ["thingName:ab*", {"abc", "abd", "abcefg"}],
        ["thingName:ab?", {"abc", "abd"}],
        ["*", {"abc", "abd", "bbe", "abcefg", "uuuabc", "bbefg"}],
        ["  ", set()],
    ],
)
@mock_aws
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
        assert "thingId" in thing


@mock_aws
def test_search_things_include_group_names():
    client = boto3.client("iot", region_name="ap-northeast-1")

    thing_name = "test-thing-name"
    client.create_thing(thingName=thing_name)

    client.create_thing_group(thingGroupName="TestGroup1")
    client.create_thing_group(thingGroupName="AnotherGroup")
    client.create_thing_group(thingGroupName="GroupWithoutMembers")

    client.add_thing_to_thing_group(thingName=thing_name, thingGroupName="TestGroup1")
    client.add_thing_to_thing_group(thingName=thing_name, thingGroupName="AnotherGroup")

    resp = client.search_index(queryString=f"thingName:{thing_name}")
    assert len(resp["things"]) == 1
    assert resp["things"][0]["thingGroupNames"] == ["TestGroup1", "AnotherGroup"]


@pytest.mark.parametrize(
    "query_string,results",
    [
        ["attributes.attr0:abc", {"abc"}],
        ["attributes.attr1:abc", set()],
        ["attributes.undefined:abc", set()],
        ["attributes.attr1", set()],
        ["attributes.attr1:", set()],
    ],
)
@mock_aws
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


@pytest.mark.parametrize(
    "query_string,results",
    [
        ["thingTypeName:foo", {"foo"}],
        ["thingTypeName:nonexisting", set()],
        ["thingTypeName:b*", {"bar", "baz"}],
        ["thingTypeName:ba.", {"bar", "baz"}],
        ["thingTypeName:b.", set()],
    ],
)
@mock_aws
def test_search_by_thing_type(query_string, results):
    client = boto3.client("iot", region_name="ap-northeast-1")

    for name in ["foo", "bar", "baz"]:
        client.create_thing_type(thingTypeName=name)
        client.create_thing(thingName=name, thingTypeName=name)

    client.create_thing(thingName="theOneWithoutThingTypeSet")

    resp = client.search_index(queryString=query_string)

    assert resp["thingGroups"] == []

    thing_names = {t["thingName"] for t in resp["things"]}
    assert thing_names == results


@pytest.mark.parametrize(
    "query_string,results",
    [
        ["thingGroupNames:foothinggroup", {"foo"}],
        ["thingGroupNames:foobillinggroup", {"foo"}],
        ["thingGroupNames:.*billinggroup", {"foo", "bar", "baz"}],
        ["thingGroupNames:.*thinggroup", {"foo", "bar", "baz"}],
        ["thingGroupNames:ba.*group", {"bar", "baz"}],
    ],
)
@mock_aws
def test_search_by_thing_groups_and_billing_groups(query_string, results):
    client = boto3.client("iot", region_name="ap-northeast-1")

    for name in ["foo", "bar", "baz"]:
        client.create_thing_group(thingGroupName=f"{name}thinggroup")
        client.create_billing_group(billingGroupName=f"{name}billinggroup")
        client.create_thing(thingName=name, billingGroupName=f"{name}billinggroup")
        client.add_thing_to_thing_group(
            thingName=name, thingGroupName=f"{name}thinggroup"
        )

    client.create_thing(thingName="theOneWithoutAnythingSet")

    resp = client.search_index(queryString=query_string)

    assert resp["thingGroups"] == []

    thing_names = {t["thingName"] for t in resp["things"]}
    assert thing_names == results


@pytest.mark.parametrize(
    "query_string, results",
    [
        # AND
        ("thingTypeName:type1 AND attributes.attr2:val2", {"thing1", "thing3"}),
        ("thingTypeName:type1 AND attributes.unknown:undefined", set()),
        ("* AND *", {"thing1", "thing2", "thing3"}),
        # Implicit AND
        ("thingTypeName:type1 attributes.attr2:val2", {"thing1", "thing3"}),
        ("* *", {"thing1", "thing2", "thing3"}),
        # OR
        ("thingTypeName:type2 OR attributes.attr1:val4", {"thing2", "thing3"}),
        ("thingTypeName:type2 OR attributes.other.key:value", {"thing2"}),
        # NOT
        ("NOT thingTypeName:type2", {"thing1", "thing3"}),
        # Combination
        (
            "(thingTypeName:type1 AND attributes.attr1:val1) OR (thingTypeName:type2 AND attributes.attr1:val1)",
            {"thing1", "thing2"},
        ),
        ("thingTypeName:type1 AND NOT attributes.attr1:val1", {"thing3"}),
        # More complex
        (
            "((thingTypeName:type1 OR thingTypeName:type2) AND attributes.attr1:val1) AND NOT attributes.attr2:val2",
            {"thing2"},
        ),
        # Negation
        ("-thingTypeName:type2", {"thing1", "thing3"}),
        ("-thingName:thing1", {"thing2", "thing3"}),
        ("-attributes.attr1:val1", {"thing3"}),
        ("(thingTypeName:type1 AND -attributes.attr1:val1)", {"thing3"}),
        (
            "((thingTypeName:type1 OR thingTypeName:type2) AND -attributes.attr2:val2) AND attributes.attr1:val1",
            {"thing2"},
        ),
    ],
)
@mock_aws
def test_search_logical_operators(query_string, results):
    client = boto3.client("iot", region_name="ap-northeast-1")

    client.create_thing_type(thingTypeName="type1")
    client.create_thing_type(thingTypeName="type2")

    client.create_thing(
        thingName="thing1",
        thingTypeName="type1",
        attributePayload={"attributes": {"attr1": "val1", "attr2": "val2"}},
    )
    client.create_thing(
        thingName="thing2",
        thingTypeName="type2",
        attributePayload={"attributes": {"attr1": "val1", "attr2": "val3"}},
    )
    client.create_thing(
        thingName="thing3",
        thingTypeName="type1",
        attributePayload={"attributes": {"attr1": "val4", "attr2": "val2"}},
    )

    resp = client.search_index(queryString=query_string)
    thing_names = {t["thingName"] for t in resp["things"]}
    assert thing_names == results, (
        f"Query failed: {query_string} | Expected: {results}, Got: {thing_names}"
    )


@pytest.mark.parametrize(
    "query_string, results",
    [
        # Thing groups
        ("(thingTypeName:type1 AND thingGroupNames:group1)", {"thing1", "thing3"}),
        ("thingTypeName:type1 AND thingGroupNames:group2", set()),
        ("thingTypeName:type2 AND thingGroupNames:group2", {"thing2"}),
        # Billing groups
        ("(thingTypeName:type1 AND thingGroupNames:billing1)", {"thing1"}),
        ("thingTypeName:type2 AND thingGroupNames:billing2", {"thing4"}),
        # Mixed groups
        (
            "(thingGroupNames:group1 OR thingGroupNames:billing2)",
            {"thing1", "thing3", "thing4"},
        ),
        # More complex
        (
            "((thingGroupNames:group1 OR thingGroupNames:group2) AND thingTypeName:type1)",
            {"thing1", "thing3"},
        ),
        ("NOT (thingGroupNames:group1 OR thingGroupNames:group2)", {"thing4"}),
        ("(thingTypeName:type1 AND -thingGroupNames:group2)", {"thing1", "thing3"}),
        ("-(thingGroupNames:group1 OR thingGroupNames:group2)", {"thing4"}),
    ],
)
@mock_aws
def test_search_logical_operators_with_groups(query_string, results):
    client = boto3.client("iot", region_name="ap-northeast-1")

    # Thing Types
    client.create_thing_type(thingTypeName="type1")
    client.create_thing_type(thingTypeName="type2")

    # Thing Groups
    client.create_thing_group(thingGroupName="group1")
    client.create_thing_group(thingGroupName="group2")

    # Billing Groups
    client.create_billing_group(billingGroupName="billing1")
    client.create_billing_group(billingGroupName="billing2")

    # Things
    client.create_thing(thingName="thing1", thingTypeName="type1")
    client.create_thing(thingName="thing2", thingTypeName="type2")
    client.create_thing(thingName="thing3", thingTypeName="type1")
    client.create_thing(thingName="thing4", thingTypeName="type2")

    # Associations
    client.add_thing_to_thing_group(thingName="thing1", thingGroupName="group1")
    client.add_thing_to_thing_group(thingName="thing2", thingGroupName="group2")
    client.add_thing_to_thing_group(thingName="thing3", thingGroupName="group1")
    client.add_thing_to_billing_group(thingName="thing1", billingGroupName="billing1")
    client.add_thing_to_billing_group(thingName="thing4", billingGroupName="billing2")

    resp = client.search_index(queryString=query_string)
    thing_names = {t["thingName"] for t in resp["things"]}
    assert thing_names == results, (
        f"Query failed: {query_string} | Expected: {results}, Got: {thing_names}"
    )


@mock_aws
def test_search_by_thing_type_no_thing_type_set():
    client = boto3.client("iot", region_name="ap-northeast-1")
    client.create_thing(thingName="thing_without_type")

    resp = client.search_index(queryString="thingTypeName:some_type")
    assert len(resp["things"]) == 0


@pytest.mark.parametrize(
    "invalid_query",
    [
        "thingName:thing1 AND",
        "thingName:thing1 OR",
        "NOT",
        "(thingName:thing1",
        "thingName:thing1)",
        "AND thingName:thing1",
        "OR thingName:thing1",
        "thingName:thing1 AND OR thingName:thing2",
        "NOT AND thingName:thing2",
        "thingName:thing1 OR NOT",
        "thingName:thing1 AND NOT",
        ")thingName:thing1",
        "(thingName:thing1 thingName:thing2",
        "()",
    ],
)
@mock_aws
def test_search_invalid_queries(invalid_query):
    client = boto3.client("iot", region_name="ap-northeast-1")
    client.create_thing(thingName="thing1")

    with pytest.raises(ClientError) as exc:
        client.search_index(queryString=invalid_query)
    assert exc.value.response["Error"]["Code"] == "InvalidRequestException"
