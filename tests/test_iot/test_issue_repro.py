import boto3

from moto import mock_aws


@mock_aws
def test_list_thing_principals_v2():
    # 1. Create a dummy AWS IoT client
    client = boto3.client("iot", region_name="us-east-1")
    thing_name = "my-test-thing"

    # 2. Create a Thing (required to list principals)
    client.create_thing(thingName=thing_name)

    # 3. Call the newly implemented V2 function
    # (This would raise NotImplementedError before our fix)
    response = client.list_thing_principals_v2(thingName=thing_name)

    # 4. Verify the response contains the V2 specific key
    assert "thingPrincipalObjects" in response
    assert response["thingPrincipalObjects"] == []
