import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_batch_items_returns_all(create_user_table):
    dynamodb = create_user_table
    returned_items = dynamodb.batch_get_item(
        RequestItems={
            "users": {
                "Keys": [
                    {"username": {"S": "user0"}},
                    {"username": {"S": "user1"}},
                    {"username": {"S": "user2"}},
                    {"username": {"S": "user3"}},
                ],
                "ConsistentRead": True,
            }
        }
    )["Responses"]["users"]
    assert len(returned_items) == 3
    assert {"username": {"S": "user1"}, "binaryfoo": {"B": b"bar"}} in returned_items
    assert {"username": {"S": "user2"}, "foo": {"S": "bar"}} in returned_items
    assert {"username": {"S": "user3"}, "foo": {"S": "bar"}} in returned_items


@mock_aws
def test_batch_items_throws_exception_when_requesting_100_items_for_single_table(
    create_user_table,
):
    dynamodb = create_user_table
    with pytest.raises(ClientError) as ex:
        dynamodb.batch_get_item(
            RequestItems={
                "users": {
                    "Keys": [
                        {"username": {"S": "user" + str(i)}} for i in range(0, 104)
                    ],
                    "ConsistentRead": True,
                }
            }
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    msg = ex.value.response["Error"]["Message"]
    assert (
        msg
        == "1 validation error detected: Value at 'requestItems.users.member.keys' failed to satisfy constraint: Member must have length less than or equal to 100"
    )


@mock_aws
def test_batch_items_throws_exception_when_requesting_100_items_across_all_tables(
    create_user_table,
):
    dynamodb = create_user_table
    with pytest.raises(ClientError) as ex:
        dynamodb.batch_get_item(
            RequestItems={
                "users": {
                    "Keys": [
                        {"username": {"S": "user" + str(i)}} for i in range(0, 75)
                    ],
                    "ConsistentRead": True,
                },
                "users2": {
                    "Keys": [
                        {"username": {"S": "user" + str(i)}} for i in range(0, 75)
                    ],
                    "ConsistentRead": True,
                },
            }
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Too many items requested for the BatchGetItem call"


@mock_aws
def test_batch_items_with_basic_projection_expression(create_user_table):
    dynamodb = create_user_table
    returned_items = dynamodb.batch_get_item(
        RequestItems={
            "users": {
                "Keys": [
                    {"username": {"S": "user0"}},
                    {"username": {"S": "user1"}},
                    {"username": {"S": "user2"}},
                    {"username": {"S": "user3"}},
                ],
                "ConsistentRead": True,
                "ProjectionExpression": "username",
            }
        }
    )["Responses"]["users"]

    assert len(returned_items) == 3
    assert [item["username"]["S"] for item in returned_items] == [
        "user1",
        "user2",
        "user3",
    ]
    assert [item.get("foo") for item in returned_items] == [None, None, None]

    # The projection expression should not remove data from storage
    returned_items = dynamodb.batch_get_item(
        RequestItems={
            "users": {
                "Keys": [
                    {"username": {"S": "user0"}},
                    {"username": {"S": "user1"}},
                    {"username": {"S": "user2"}},
                    {"username": {"S": "user3"}},
                ],
                "ConsistentRead": True,
            }
        }
    )["Responses"]["users"]

    assert len(returned_items) == 3
    assert {"username": {"S": "user1"}, "binaryfoo": {"B": b"bar"}} in returned_items
    assert {"username": {"S": "user2"}, "foo": {"S": "bar"}} in returned_items
    assert {"username": {"S": "user3"}, "foo": {"S": "bar"}} in returned_items


@mock_aws
def test_batch_items_with_basic_projection_expression_and_attr_expression_names(
    create_user_table,
):
    dynamodb = create_user_table
    returned_items = dynamodb.batch_get_item(
        RequestItems={
            "users": {
                "Keys": [
                    {"username": {"S": "user0"}},
                    {"username": {"S": "user1"}},
                    {"username": {"S": "user2"}},
                    {"username": {"S": "user3"}},
                ],
                "ConsistentRead": True,
                "ProjectionExpression": "#rl",
                "ExpressionAttributeNames": {"#rl": "username"},
            }
        }
    )["Responses"]["users"]

    assert len(returned_items) == 3
    assert {"username": {"S": "user1"}} in returned_items
    assert {"username": {"S": "user2"}} in returned_items
    assert {"username": {"S": "user3"}} in returned_items


@mock_aws
def test_batch_items_should_throw_exception_for_duplicate_request(create_user_table):
    client = create_user_table
    with pytest.raises(ClientError) as ex:
        client.batch_get_item(
            RequestItems={
                "users": {
                    "Keys": [
                        {"username": {"S": "user0"}},
                        {"username": {"S": "user0"}},
                    ],
                    "ConsistentRead": True,
                }
            }
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Provided list of item keys contains duplicates"


@mock_aws
def test_batch_items_should_return_16mb_max(create_user_table):
    """
    A single operation can retrieve up to 16 MB of data [...]. BatchGetItem returns a partial result if the response size limit is exceeded [..].

    For example, if you ask to retrieve 100 items, but each individual item is 300 KB in size,
    the system returns 52 items (so as not to exceed the 16 MB limit).

    It also returns an appropriate UnprocessedKeys value so you can get the next page of results.
    If desired, your application can include its own logic to assemble the pages of results into one dataset.
    """
    client = create_user_table
    # Fill table with all the data
    for i in range(100):
        client.put_item(
            TableName="users",
            Item={"username": {"S": f"largedata{i}"}, "foo": {"S": "x" * 300000}},
        )

    resp = client.batch_get_item(
        RequestItems={
            "users": {
                "Keys": [{"username": {"S": f"largedata{i}"}} for i in range(75)],
                "ConsistentRead": True,
            }
        }
    )

    assert len(resp["Responses"]["users"]) == 55
    unprocessed_keys = resp["UnprocessedKeys"]["users"]["Keys"]
    # 75 requested, 55 returned --> 20 unprocessed
    assert len(unprocessed_keys) == 20

    # Keys 55-75 are unprocessed
    assert {"username": {"S": "largedata55"}} in unprocessed_keys
    assert {"username": {"S": "largedata65"}} in unprocessed_keys

    # Keys 0-55 are processed in the regular response, so they shouldn't show up here
    assert {"username": {"S": "largedata45"}} not in unprocessed_keys
