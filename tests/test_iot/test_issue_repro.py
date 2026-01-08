import boto3
import pytest
from moto import mock_aws


@mock_aws
def test_list_thing_principals_v2():
    # Create a fake AWS IoT client
    client = boto3.client("iot", region_name="us-east-1")
    thing_name = "my-test-thing"

    # 2. Create a Thing (otherwise you won't be able to find anything).
    client.create_thing(thingName=thing_name)

    # 3. Call the newly written V2 function!
    # (If the IF statement is not written correctly, this will result in an error saying "Not Implemented")
    response = client.list_thing_principals_v2(thingName=thing_name)

    # 4. Verify if the returned data includes the V2-specific field "thingPrincipalObjects"."
    assert "thingPrincipalObjects" in response
    # Since we haven't bound certificates yet, the list should be empty, but the key must exist.
    assert response["thingPrincipalObjects"] == []

    print("\n🎉 Test successful! V2 functionality is working properly!")
