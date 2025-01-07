import boto3

from moto import mock_aws


@mock_aws
def test_validate_default_indexing_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    indexing_config = client.get_indexing_configuration()

    thingIndexingConfiguration = indexing_config["thingIndexingConfiguration"]
    assert thingIndexingConfiguration["thingIndexingMode"] in [
        "OFF",
        "REGISTRY",
        "REGISTRY_AND_SHADOW",
    ]

    thingGroupIndexingConfiguration = indexing_config["thingGroupIndexingConfiguration"]
    assert thingGroupIndexingConfiguration["thingGroupIndexingMode"] in ["ON", "OFF"]


@mock_aws
def test_update_indexing_mode():
    client = boto3.client("iot", region_name="us-east-1")
    client.update_indexing_configuration(
        thingIndexingConfiguration={
            "thingIndexingMode": "REGISTRY",
            "thingConnectivityIndexingMode": "STATUS",
            "deviceDefenderIndexingMode": "VIOLATIONS",
            "namedShadowIndexingMode": "ON",
            "managedFields": [{"name": "field1", "type": "String"}],
            "customFields": [{"name": "custom_field1", "type": "Boolean"}],
            "filter": {"namedShadowNames": ["shadow_1", "shadow_2"]},
        },
        thingGroupIndexingConfiguration={
            "thingGroupIndexingMode": "ON",
            "managedFields": [{"name": "thing_field_1", "type": "String"}],
            "customFields": [{"name": "thing_custom_field", "type": "Number"}],
        },
    )

    indexing_config = client.get_indexing_configuration()

    thingIndexingConfiguration = indexing_config["thingIndexingConfiguration"]
    assert thingIndexingConfiguration["thingIndexingMode"] == "REGISTRY"
    assert thingIndexingConfiguration["thingConnectivityIndexingMode"] == "STATUS"
    assert thingIndexingConfiguration["deviceDefenderIndexingMode"] == "VIOLATIONS"
    assert thingIndexingConfiguration["namedShadowIndexingMode"] == "ON"
    assert thingIndexingConfiguration["managedFields"] == [
        {"name": "field1", "type": "String"}
    ]
    assert thingIndexingConfiguration["customFields"] == [
        {"name": "custom_field1", "type": "Boolean"}
    ]

    thingGroupIndexingConfiguration = indexing_config["thingGroupIndexingConfiguration"]
    assert thingGroupIndexingConfiguration["thingGroupIndexingMode"] == "ON"
    assert thingGroupIndexingConfiguration["managedFields"] == [
        {"name": "thing_field_1", "type": "String"}
    ]
    assert thingGroupIndexingConfiguration["customFields"] == [
        {"name": "thing_custom_field", "type": "Number"}
    ]
