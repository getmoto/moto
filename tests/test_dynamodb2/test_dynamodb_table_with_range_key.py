from __future__ import unicode_literals

from decimal import Decimal

import boto
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
import sure  # noqa
from freezegun import freeze_time
from nose.tools import assert_raises

from moto import mock_dynamodb2, mock_dynamodb2_deprecated
from boto.exception import JSONResponseError
from tests.helpers import requires_boto_gte

try:
    from boto.dynamodb2.fields import GlobalAllIndex, HashKey, RangeKey, AllIndex
    from boto.dynamodb2.table import Item, Table
    from boto.dynamodb2.types import STRING, NUMBER
    from boto.dynamodb2.exceptions import ValidationException
    from boto.dynamodb2.exceptions import ConditionalCheckFailedException
except ImportError:
    pass


def create_table():
    table = Table.create(
        "messages",
        schema=[HashKey("forum_name"), RangeKey("subject")],
        throughput={"read": 10, "write": 10},
    )
    return table


def create_table_with_local_indexes():
    table = Table.create(
        "messages",
        schema=[HashKey("forum_name"), RangeKey("subject")],
        throughput={"read": 10, "write": 10},
        indexes=[
            AllIndex(
                "threads_index",
                parts=[
                    HashKey("forum_name", data_type=STRING),
                    RangeKey("threads", data_type=NUMBER),
                ],
            )
        ],
    )
    return table


def iterate_results(res):
    for i in res:
        pass


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
@freeze_time("2012-01-14")
def test_create_table():
    table = create_table()
    expected = {
        "Table": {
            "AttributeDefinitions": [
                {"AttributeName": "forum_name", "AttributeType": "S"},
                {"AttributeName": "subject", "AttributeType": "S"},
            ],
            "ProvisionedThroughput": {
                "NumberOfDecreasesToday": 0,
                "WriteCapacityUnits": 10,
                "ReadCapacityUnits": 10,
            },
            "TableSizeBytes": 0,
            "TableName": "messages",
            "TableStatus": "ACTIVE",
            "TableArn": "arn:aws:dynamodb:us-east-1:123456789011:table/messages",
            "KeySchema": [
                {"KeyType": "HASH", "AttributeName": "forum_name"},
                {"KeyType": "RANGE", "AttributeName": "subject"},
            ],
            "LocalSecondaryIndexes": [],
            "ItemCount": 0,
            "CreationDateTime": 1326499200.0,
            "GlobalSecondaryIndexes": [],
        }
    }
    table.describe().should.equal(expected)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
@freeze_time("2012-01-14")
def test_create_table_with_local_index():
    table = create_table_with_local_indexes()
    expected = {
        "Table": {
            "AttributeDefinitions": [
                {"AttributeName": "forum_name", "AttributeType": "S"},
                {"AttributeName": "subject", "AttributeType": "S"},
                {"AttributeName": "threads", "AttributeType": "N"},
            ],
            "ProvisionedThroughput": {
                "NumberOfDecreasesToday": 0,
                "WriteCapacityUnits": 10,
                "ReadCapacityUnits": 10,
            },
            "TableSizeBytes": 0,
            "TableName": "messages",
            "TableStatus": "ACTIVE",
            "TableArn": "arn:aws:dynamodb:us-east-1:123456789011:table/messages",
            "KeySchema": [
                {"KeyType": "HASH", "AttributeName": "forum_name"},
                {"KeyType": "RANGE", "AttributeName": "subject"},
            ],
            "LocalSecondaryIndexes": [
                {
                    "IndexName": "threads_index",
                    "KeySchema": [
                        {"AttributeName": "forum_name", "KeyType": "HASH"},
                        {"AttributeName": "threads", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            "ItemCount": 0,
            "CreationDateTime": 1326499200.0,
            "GlobalSecondaryIndexes": [],
        }
    }
    table.describe().should.equal(expected)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_delete_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()
    table = create_table()
    conn.list_tables()["TableNames"].should.have.length_of(1)

    table.delete()
    conn.list_tables()["TableNames"].should.have.length_of(0)
    conn.delete_table.when.called_with("messages").should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_update_table_throughput():
    table = create_table()
    table.throughput["read"].should.equal(10)
    table.throughput["write"].should.equal(10)
    table.update(throughput={"read": 5, "write": 15})

    table.throughput["read"].should.equal(5)
    table.throughput["write"].should.equal(15)

    table.update(throughput={"read": 5, "write": 6})

    table.describe()

    table.throughput["read"].should.equal(5)
    table.throughput["write"].should.equal(6)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_item_add_and_describe_and_update():
    table = create_table()
    ok = table.put_item(
        data={
            "forum_name": "LOLCat Forum",
            "subject": "Check this out!",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User A",
            "ReceivedTime": "12/9/2011 11:36:03 PM",
        }
    )
    ok.should.equal(True)

    table.get_item(
        forum_name="LOLCat Forum", subject="Check this out!"
    ).should_not.be.none

    returned_item = table.get_item(forum_name="LOLCat Forum", subject="Check this out!")
    dict(returned_item).should.equal(
        {
            "forum_name": "LOLCat Forum",
            "subject": "Check this out!",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User A",
            "ReceivedTime": "12/9/2011 11:36:03 PM",
        }
    )

    returned_item["SentBy"] = "User B"
    returned_item.save(overwrite=True)

    returned_item = table.get_item(forum_name="LOLCat Forum", subject="Check this out!")
    dict(returned_item).should.equal(
        {
            "forum_name": "LOLCat Forum",
            "subject": "Check this out!",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User B",
            "ReceivedTime": "12/9/2011 11:36:03 PM",
        }
    )


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_item_partial_save():
    table = create_table()

    data = {
        "forum_name": "LOLCat Forum",
        "subject": "The LOLz",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
    }

    table.put_item(data=data)
    returned_item = table.get_item(forum_name="LOLCat Forum", subject="The LOLz")

    returned_item["SentBy"] = "User B"
    returned_item.partial_save()

    returned_item = table.get_item(forum_name="LOLCat Forum", subject="The LOLz")
    dict(returned_item).should.equal(
        {
            "forum_name": "LOLCat Forum",
            "subject": "The LOLz",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User B",
        }
    )


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_item_put_without_table():
    table = Table("undeclared-table")
    item_data = {
        "forum_name": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = Item(table, item_data)
    item.save.when.called_with().should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_get_missing_item():
    table = create_table()

    table.get_item.when.called_with(hash_key="tester", range_key="other").should.throw(
        ValidationException
    )


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_get_item_with_undeclared_table():
    table = Table("undeclared-table")
    table.get_item.when.called_with(test_hash=3241526475).should.throw(
        JSONResponseError
    )


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_get_item_without_range_key():
    table = Table.create(
        "messages",
        schema=[HashKey("test_hash"), RangeKey("test_range")],
        throughput={"read": 10, "write": 10},
    )

    hash_key = 3241526475
    range_key = 1234567890987
    table.put_item(data={"test_hash": hash_key, "test_range": range_key})
    table.get_item.when.called_with(test_hash=hash_key).should.throw(
        ValidationException
    )


@requires_boto_gte("2.30.0")
@mock_dynamodb2_deprecated
def test_delete_item():
    table = create_table()
    item_data = {
        "forum_name": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = Item(table, item_data)
    item["subject"] = "Check this out!"
    item.save()
    table.count().should.equal(1)

    response = item.delete()
    response.should.equal(True)

    table.count().should.equal(0)
    # Deletes are idempotent
    item.delete().should.equal(True)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_delete_item_with_undeclared_table():
    table = Table("undeclared-table")
    item_data = {
        "forum_name": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = Item(table, item_data)
    item.delete.when.called_with().should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_query():
    table = create_table()

    item_data = {
        "forum_name": "LOLCat Forum",
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
        "subject": "Check this out!",
    }
    item = Item(table, item_data)
    item.save(overwrite=True)

    item["forum_name"] = "the-key"
    item["subject"] = "456"
    item.save(overwrite=True)

    item["forum_name"] = "the-key"
    item["subject"] = "123"
    item.save(overwrite=True)

    item["forum_name"] = "the-key"
    item["subject"] = "789"
    item.save(overwrite=True)

    table.count().should.equal(4)

    results = table.query_2(forum_name__eq="the-key", subject__gt="1", consistent=True)
    expected = ["123", "456", "789"]
    for index, item in enumerate(results):
        item["subject"].should.equal(expected[index])

    results = table.query_2(forum_name__eq="the-key", subject__gt="1", reverse=True)
    for index, item in enumerate(results):
        item["subject"].should.equal(expected[len(expected) - 1 - index])

    results = table.query_2(forum_name__eq="the-key", subject__gt="1", consistent=True)
    sum(1 for _ in results).should.equal(3)

    results = table.query_2(
        forum_name__eq="the-key", subject__gt="234", consistent=True
    )
    sum(1 for _ in results).should.equal(2)

    results = table.query_2(forum_name__eq="the-key", subject__gt="9999")
    sum(1 for _ in results).should.equal(0)

    results = table.query_2(forum_name__eq="the-key", subject__beginswith="12")
    sum(1 for _ in results).should.equal(1)

    results = table.query_2(forum_name__eq="the-key", subject__beginswith="7")
    sum(1 for _ in results).should.equal(1)

    results = table.query_2(forum_name__eq="the-key", subject__between=["567", "890"])
    sum(1 for _ in results).should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_query_with_undeclared_table():
    table = Table("undeclared")
    results = table.query(
        forum_name__eq="Amazon DynamoDB", subject__beginswith="DynamoDB", limit=1
    )
    iterate_results.when.called_with(results).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_scan():
    table = create_table()
    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item_data["forum_name"] = "the-key"
    item_data["subject"] = "456"

    item = Item(table, item_data)
    item.save()

    item["forum_name"] = "the-key"
    item["subject"] = "123"
    item.save()

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User B",
        "ReceivedTime": "12/9/2011 11:36:09 PM",
        "Ids": set([1, 2, 3]),
        "PK": 7,
    }

    item_data["forum_name"] = "the-key"
    item_data["subject"] = "789"

    item = Item(table, item_data)
    item.save()

    results = table.scan()
    sum(1 for _ in results).should.equal(3)

    results = table.scan(SentBy__eq="User B")
    sum(1 for _ in results).should.equal(1)

    results = table.scan(Body__beginswith="http")
    sum(1 for _ in results).should.equal(3)

    results = table.scan(Ids__null=False)
    sum(1 for _ in results).should.equal(1)

    results = table.scan(Ids__null=True)
    sum(1 for _ in results).should.equal(2)

    results = table.scan(PK__between=[8, 9])
    sum(1 for _ in results).should.equal(0)

    results = table.scan(PK__between=[5, 8])
    sum(1 for _ in results).should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_scan_with_undeclared_table():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()
    conn.scan.when.called_with(
        table_name="undeclared-table",
        scan_filter={
            "SentBy": {
                "AttributeValueList": [{"S": "User B"}],
                "ComparisonOperator": "EQ",
            }
        },
    ).should.throw(JSONResponseError)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_write_batch():
    table = create_table()
    with table.batch_write() as batch:
        batch.put_item(
            data={
                "forum_name": "the-key",
                "subject": "123",
                "Body": "http://url_to_lolcat.gif",
                "SentBy": "User A",
                "ReceivedTime": "12/9/2011 11:36:03 PM",
            }
        )
        batch.put_item(
            data={
                "forum_name": "the-key",
                "subject": "789",
                "Body": "http://url_to_lolcat.gif",
                "SentBy": "User B",
                "ReceivedTime": "12/9/2011 11:36:03 PM",
            }
        )

    table.count().should.equal(2)
    with table.batch_write() as batch:
        batch.delete_item(forum_name="the-key", subject="789")

    table.count().should.equal(1)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_batch_read():
    table = create_table()
    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }

    item_data["forum_name"] = "the-key"
    item_data["subject"] = "456"

    item = Item(table, item_data)
    item.save()

    item = Item(table, item_data)
    item_data["forum_name"] = "the-key"
    item_data["subject"] = "123"
    item.save()

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User B",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
        "Ids": set([1, 2, 3]),
        "PK": 7,
    }
    item = Item(table, item_data)
    item_data["forum_name"] = "another-key"
    item_data["subject"] = "789"
    item.save()
    results = table.batch_get(
        keys=[
            {"forum_name": "the-key", "subject": "123"},
            {"forum_name": "another-key", "subject": "789"},
        ]
    )

    # Iterate through so that batch_item gets called
    count = len([x for x in results])
    count.should.equal(2)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_get_key_fields():
    table = create_table()
    kf = table.get_key_fields()
    kf.should.equal(["forum_name", "subject"])


@mock_dynamodb2_deprecated
def test_create_with_global_indexes():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    Table.create(
        "messages",
        schema=[HashKey("subject"), RangeKey("version")],
        global_indexes=[
            GlobalAllIndex(
                "topic-created_at-index",
                parts=[HashKey("topic"), RangeKey("created_at", data_type="N")],
                throughput={"read": 6, "write": 1},
            )
        ],
    )

    table_description = conn.describe_table("messages")
    table_description["Table"]["GlobalSecondaryIndexes"].should.equal(
        [
            {
                "IndexName": "topic-created_at-index",
                "KeySchema": [
                    {"AttributeName": "topic", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 6,
                    "WriteCapacityUnits": 1,
                },
                "IndexStatus": "ACTIVE",
            }
        ]
    )


@mock_dynamodb2_deprecated
def test_query_with_global_indexes():
    table = Table.create(
        "messages",
        schema=[HashKey("subject"), RangeKey("version")],
        global_indexes=[
            GlobalAllIndex(
                "topic-created_at-index",
                parts=[HashKey("topic"), RangeKey("created_at", data_type="N")],
                throughput={"read": 6, "write": 1},
            ),
            GlobalAllIndex(
                "status-created_at-index",
                parts=[HashKey("status"), RangeKey("created_at", data_type="N")],
                throughput={"read": 2, "write": 1},
            ),
        ],
    )

    item_data = {
        "subject": "Check this out!",
        "version": "1",
        "created_at": 0,
        "status": "inactive",
    }
    item = Item(table, item_data)
    item.save(overwrite=True)

    item["version"] = "2"
    item.save(overwrite=True)

    results = table.query(status__eq="active")
    list(results).should.have.length_of(0)


@mock_dynamodb2_deprecated
def test_query_with_local_indexes():
    table = create_table_with_local_indexes()
    item_data = {
        "forum_name": "Cool Forum",
        "subject": "Check this out!",
        "version": "1",
        "threads": 1,
        "status": "inactive",
    }
    item = Item(table, item_data)
    item.save(overwrite=True)

    item["version"] = "2"
    item.save(overwrite=True)
    results = table.query(
        forum_name__eq="Cool Forum", index="threads_index", threads__eq=1
    )
    list(results).should.have.length_of(1)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_query_filter_eq():
    table = create_table_with_local_indexes()
    item_data = [
        {
            "forum_name": "Cool Forum",
            "subject": "Check this out!",
            "version": "1",
            "threads": 1,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Read this now!",
            "version": "1",
            "threads": 5,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Please read this... please",
            "version": "1",
            "threads": 0,
        },
    ]
    for data in item_data:
        item = Item(table, data)
        item.save(overwrite=True)
    results = table.query_2(
        forum_name__eq="Cool Forum", index="threads_index", threads__eq=5
    )
    list(results).should.have.length_of(1)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_query_filter_lt():
    table = create_table_with_local_indexes()
    item_data = [
        {
            "forum_name": "Cool Forum",
            "subject": "Check this out!",
            "version": "1",
            "threads": 1,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Read this now!",
            "version": "1",
            "threads": 5,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Please read this... please",
            "version": "1",
            "threads": 0,
        },
    ]
    for data in item_data:
        item = Item(table, data)
        item.save(overwrite=True)

    results = table.query(
        forum_name__eq="Cool Forum", index="threads_index", threads__lt=5
    )
    results = list(results)
    results.should.have.length_of(2)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_query_filter_gt():
    table = create_table_with_local_indexes()
    item_data = [
        {
            "forum_name": "Cool Forum",
            "subject": "Check this out!",
            "version": "1",
            "threads": 1,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Read this now!",
            "version": "1",
            "threads": 5,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Please read this... please",
            "version": "1",
            "threads": 0,
        },
    ]
    for data in item_data:
        item = Item(table, data)
        item.save(overwrite=True)

    results = table.query(
        forum_name__eq="Cool Forum", index="threads_index", threads__gt=1
    )
    list(results).should.have.length_of(1)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_query_filter_lte():
    table = create_table_with_local_indexes()
    item_data = [
        {
            "forum_name": "Cool Forum",
            "subject": "Check this out!",
            "version": "1",
            "threads": 1,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Read this now!",
            "version": "1",
            "threads": 5,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Please read this... please",
            "version": "1",
            "threads": 0,
        },
    ]
    for data in item_data:
        item = Item(table, data)
        item.save(overwrite=True)

    results = table.query(
        forum_name__eq="Cool Forum", index="threads_index", threads__lte=5
    )
    list(results).should.have.length_of(3)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_query_filter_gte():
    table = create_table_with_local_indexes()
    item_data = [
        {
            "forum_name": "Cool Forum",
            "subject": "Check this out!",
            "version": "1",
            "threads": 1,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Read this now!",
            "version": "1",
            "threads": 5,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Please read this... please",
            "version": "1",
            "threads": 0,
        },
    ]
    for data in item_data:
        item = Item(table, data)
        item.save(overwrite=True)

    results = table.query(
        forum_name__eq="Cool Forum", index="threads_index", threads__gte=1
    )
    list(results).should.have.length_of(2)


@requires_boto_gte("2.9")
@mock_dynamodb2_deprecated
def test_query_non_hash_range_key():
    table = create_table_with_local_indexes()
    item_data = [
        {
            "forum_name": "Cool Forum",
            "subject": "Check this out!",
            "version": "1",
            "threads": 1,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Read this now!",
            "version": "3",
            "threads": 5,
        },
        {
            "forum_name": "Cool Forum",
            "subject": "Please read this... please",
            "version": "2",
            "threads": 0,
        },
    ]
    for data in item_data:
        item = Item(table, data)
        item.save(overwrite=True)

    results = table.query(forum_name__eq="Cool Forum", version__gt="2")
    results = list(results)
    results.should.have.length_of(1)

    results = table.query(forum_name__eq="Cool Forum", version__lt="3")
    results = list(results)
    results.should.have.length_of(2)


@mock_dynamodb2_deprecated
def test_reverse_query():
    conn = boto.dynamodb2.layer1.DynamoDBConnection()

    table = Table.create(
        "messages", schema=[HashKey("subject"), RangeKey("created_at", data_type="N")]
    )

    for i in range(10):
        table.put_item({"subject": "Hi", "created_at": i})

    results = table.query_2(subject__eq="Hi", created_at__lt=6, limit=4, reverse=True)

    expected = [Decimal(5), Decimal(4), Decimal(3), Decimal(2)]
    [r["created_at"] for r in results].should.equal(expected)


@mock_dynamodb2_deprecated
def test_lookup():
    from decimal import Decimal

    table = Table.create(
        "messages",
        schema=[HashKey("test_hash"), RangeKey("test_range")],
        throughput={"read": 10, "write": 10},
    )

    hash_key = 3241526475
    range_key = 1234567890987
    data = {"test_hash": hash_key, "test_range": range_key}
    table.put_item(data=data)
    message = table.lookup(hash_key, range_key)
    message.get("test_hash").should.equal(Decimal(hash_key))
    message.get("test_range").should.equal(Decimal(range_key))


@mock_dynamodb2_deprecated
def test_failed_overwrite():
    table = Table.create(
        "messages",
        schema=[HashKey("id"), RangeKey("range")],
        throughput={"read": 7, "write": 3},
    )

    data1 = {"id": "123", "range": "abc", "data": "678"}
    table.put_item(data=data1)

    data2 = {"id": "123", "range": "abc", "data": "345"}
    table.put_item(data=data2, overwrite=True)

    data3 = {"id": "123", "range": "abc", "data": "812"}
    table.put_item.when.called_with(data=data3).should.throw(
        ConditionalCheckFailedException
    )

    returned_item = table.lookup("123", "abc")
    dict(returned_item).should.equal(data2)

    data4 = {"id": "123", "range": "ghi", "data": 812}
    table.put_item(data=data4)

    returned_item = table.lookup("123", "ghi")
    dict(returned_item).should.equal(data4)


@mock_dynamodb2_deprecated
def test_conflicting_writes():
    table = Table.create("messages", schema=[HashKey("id"), RangeKey("range")])

    item_data = {"id": "123", "range": "abc", "data": "678"}
    item1 = Item(table, item_data)
    item2 = Item(table, item_data)
    item1.save()

    item1["data"] = "579"
    item2["data"] = "912"

    item1.save()
    item2.save.when.called_with().should.throw(ConditionalCheckFailedException)


"""
boto3
"""


@mock_dynamodb2
def test_boto3_create_table_with_gsi():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [{"AttributeName": "subject", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    table["TableDescription"]["GlobalSecondaryIndexes"].should.equal(
        [
            {
                "KeySchema": [{"KeyType": "HASH", "AttributeName": "subject"}],
                "IndexName": "test_gsi",
                "Projection": {"ProjectionType": "ALL"},
                "IndexStatus": "ACTIVE",
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 0,
                    "WriteCapacityUnits": 0,
                },
            }
        ]
    )

    table = dynamodb.create_table(
        TableName="users2",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [{"AttributeName": "subject", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 3,
                    "WriteCapacityUnits": 5,
                },
            }
        ],
    )
    table["TableDescription"]["GlobalSecondaryIndexes"].should.equal(
        [
            {
                "KeySchema": [{"KeyType": "HASH", "AttributeName": "subject"}],
                "IndexName": "test_gsi",
                "Projection": {"ProjectionType": "ALL"},
                "IndexStatus": "ACTIVE",
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 3,
                    "WriteCapacityUnits": 5,
                },
            }
        ]
    )


@mock_dynamodb2
def test_boto3_conditions():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("users")

    table.put_item(Item={"forum_name": "the-key", "subject": "123"})
    table.put_item(Item={"forum_name": "the-key", "subject": "456"})
    table.put_item(Item={"forum_name": "the-key", "subject": "789"})

    # Test a query returning all items
    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key") & Key("subject").gt("1"),
        ScanIndexForward=True,
    )
    expected = ["123", "456", "789"]
    for index, item in enumerate(results["Items"]):
        item["subject"].should.equal(expected[index])

    # Return all items again, but in reverse
    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key") & Key("subject").gt("1"),
        ScanIndexForward=False,
    )
    for index, item in enumerate(reversed(results["Items"])):
        item["subject"].should.equal(expected[index])

    # Filter the subjects to only return some of the results
    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key")
        & Key("subject").gt("234"),
        ConsistentRead=True,
    )
    results["Count"].should.equal(2)

    # Filter to return no results
    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key")
        & Key("subject").gt("9999")
    )
    results["Count"].should.equal(0)

    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key")
        & Key("subject").begins_with("12")
    )
    results["Count"].should.equal(1)

    results = table.query(
        KeyConditionExpression=Key("subject").begins_with("7")
        & Key("forum_name").eq("the-key")
    )
    results["Count"].should.equal(1)

    results = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key")
        & Key("subject").between("567", "890")
    )
    results["Count"].should.equal(1)


@mock_dynamodb2
def test_boto3_put_item_with_conditions():
    import botocore

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    table = dynamodb.Table("users")

    table.put_item(Item={"forum_name": "the-key", "subject": "123"})

    table.put_item(
        Item={"forum_name": "the-key-2", "subject": "1234"},
        ConditionExpression="attribute_not_exists(forum_name) AND attribute_not_exists(subject)",
    )

    table.put_item.when.called_with(
        Item={"forum_name": "the-key", "subject": "123"},
        ConditionExpression="attribute_not_exists(forum_name) AND attribute_not_exists(subject)",
    ).should.throw(botocore.exceptions.ClientError)

    table.put_item.when.called_with(
        Item={"forum_name": "bogus-key", "subject": "bogus", "test": "123"},
        ConditionExpression="attribute_exists(forum_name) AND attribute_exists(subject)",
    ).should.throw(botocore.exceptions.ClientError)


def _create_table_with_range_key():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "TestGSI",
                "KeySchema": [
                    {"AttributeName": "username", "KeyType": "HASH"},
                    {"AttributeName": "created", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            }
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
            {"AttributeName": "username", "AttributeType": "S"},
            {"AttributeName": "created", "AttributeType": "N"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    return dynamodb.Table("users")


@mock_dynamodb2
def test_update_item_range_key_set():
    table = _create_table_with_range_key()
    table.put_item(
        Item={
            "forum_name": "the-key",
            "subject": "123",
            "username": "johndoe",
            "created": Decimal("3"),
        }
    )

    item_key = {"forum_name": "the-key", "subject": "123"}
    table.update_item(
        Key=item_key,
        AttributeUpdates={
            "username": {"Action": "PUT", "Value": "johndoe2"},
            "created": {"Action": "PUT", "Value": Decimal("4")},
            "mapfield": {"Action": "PUT", "Value": {"key": "value"}},
        },
    )

    returned_item = dict(
        (k, str(v) if isinstance(v, Decimal) else v)
        for k, v in table.get_item(Key=item_key)["Item"].items()
    )
    dict(returned_item).should.equal(
        {
            "username": "johndoe2",
            "forum_name": "the-key",
            "subject": "123",
            "created": "4",
            "mapfield": {"key": "value"},
        }
    )


@mock_dynamodb2
def test_update_item_does_not_exist_is_created():
    table = _create_table_with_range_key()

    item_key = {"forum_name": "the-key", "subject": "123"}
    result = table.update_item(
        Key=item_key,
        AttributeUpdates={
            "username": {"Action": "PUT", "Value": "johndoe2"},
            "created": {"Action": "PUT", "Value": Decimal("4")},
            "mapfield": {"Action": "PUT", "Value": {"key": "value"}},
        },
        ReturnValues="ALL_OLD",
    )

    assert not result.get("Attributes")

    returned_item = dict(
        (k, str(v) if isinstance(v, Decimal) else v)
        for k, v in table.get_item(Key=item_key)["Item"].items()
    )
    dict(returned_item).should.equal(
        {
            "username": "johndoe2",
            "forum_name": "the-key",
            "subject": "123",
            "created": "4",
            "mapfield": {"key": "value"},
        }
    )


@mock_dynamodb2
def test_update_item_add_value():
    table = _create_table_with_range_key()

    table.put_item(
        Item={"forum_name": "the-key", "subject": "123", "numeric_field": Decimal("-1")}
    )

    item_key = {"forum_name": "the-key", "subject": "123"}
    table.update_item(
        Key=item_key,
        AttributeUpdates={"numeric_field": {"Action": "ADD", "Value": Decimal("2")}},
    )

    returned_item = dict(
        (k, str(v) if isinstance(v, Decimal) else v)
        for k, v in table.get_item(Key=item_key)["Item"].items()
    )
    dict(returned_item).should.equal(
        {"numeric_field": "1", "forum_name": "the-key", "subject": "123"}
    )


@mock_dynamodb2
def test_update_item_add_value_string_set():
    table = _create_table_with_range_key()

    table.put_item(
        Item={
            "forum_name": "the-key",
            "subject": "123",
            "string_set": set(["str1", "str2"]),
        }
    )

    item_key = {"forum_name": "the-key", "subject": "123"}
    table.update_item(
        Key=item_key,
        AttributeUpdates={"string_set": {"Action": "ADD", "Value": set(["str3"])}},
    )

    returned_item = dict(
        (k, str(v) if isinstance(v, Decimal) else v)
        for k, v in table.get_item(Key=item_key)["Item"].items()
    )
    dict(returned_item).should.equal(
        {
            "string_set": set(["str1", "str2", "str3"]),
            "forum_name": "the-key",
            "subject": "123",
        }
    )


@mock_dynamodb2
def test_update_item_delete_value_string_set():
    table = _create_table_with_range_key()

    table.put_item(
        Item={
            "forum_name": "the-key",
            "subject": "123",
            "string_set": set(["str1", "str2"]),
        }
    )

    item_key = {"forum_name": "the-key", "subject": "123"}
    table.update_item(
        Key=item_key,
        AttributeUpdates={"string_set": {"Action": "DELETE", "Value": set(["str2"])}},
    )

    returned_item = dict(
        (k, str(v) if isinstance(v, Decimal) else v)
        for k, v in table.get_item(Key=item_key)["Item"].items()
    )
    dict(returned_item).should.equal(
        {"string_set": set(["str1"]), "forum_name": "the-key", "subject": "123"}
    )


@mock_dynamodb2
def test_update_item_add_value_does_not_exist_is_created():
    table = _create_table_with_range_key()

    item_key = {"forum_name": "the-key", "subject": "123"}
    table.update_item(
        Key=item_key,
        AttributeUpdates={"numeric_field": {"Action": "ADD", "Value": Decimal("2")}},
    )

    returned_item = dict(
        (k, str(v) if isinstance(v, Decimal) else v)
        for k, v in table.get_item(Key=item_key)["Item"].items()
    )
    dict(returned_item).should.equal(
        {"numeric_field": "2", "forum_name": "the-key", "subject": "123"}
    )


@mock_dynamodb2
def test_update_item_with_expression():
    table = _create_table_with_range_key()

    table.put_item(Item={"forum_name": "the-key", "subject": "123", "field": "1"})

    item_key = {"forum_name": "the-key", "subject": "123"}

    table.update_item(
        Key=item_key,
        UpdateExpression="SET field = :field_value",
        ExpressionAttributeValues={":field_value": 2},
    )
    dict(table.get_item(Key=item_key)["Item"]).should.equal(
        {"field": Decimal("2"), "forum_name": "the-key", "subject": "123"}
    )

    table.update_item(
        Key=item_key,
        UpdateExpression="SET field = :field_value",
        ExpressionAttributeValues={":field_value": 3},
    )
    dict(table.get_item(Key=item_key)["Item"]).should.equal(
        {"field": Decimal("3"), "forum_name": "the-key", "subject": "123"}
    )


def assert_failure_due_to_key_not_in_schema(func, **kwargs):
    with assert_raises(ClientError) as ex:
        func(**kwargs)
    ex.exception.response["Error"]["Code"].should.equal("ValidationException")
    ex.exception.response["Error"]["Message"].should.equal(
        "The provided key element does not match the schema"
    )


@mock_dynamodb2
def test_update_item_add_with_expression():
    table = _create_table_with_range_key()

    item_key = {"forum_name": "the-key", "subject": "123"}
    current_item = {
        "forum_name": "the-key",
        "subject": "123",
        "str_set": {"item1", "item2", "item3"},
        "num_set": {1, 2, 3},
        "num_val": 6,
    }

    # Put an entry in the DB to play with
    table.put_item(Item=current_item)

    # Update item to add a string value to a string set
    table.update_item(
        Key=item_key,
        UpdateExpression="ADD str_set :v",
        ExpressionAttributeValues={":v": {"item4"}},
    )
    current_item["str_set"] = current_item["str_set"].union({"item4"})
    assert dict(table.get_item(Key=item_key)["Item"]) == current_item

    # Update item to add a string value to a non-existing set
    table.update_item(
        Key=item_key,
        UpdateExpression="ADD non_existing_str_set :v",
        ExpressionAttributeValues={":v": {"item4"}},
    )
    current_item["non_existing_str_set"] = {"item4"}
    assert dict(table.get_item(Key=item_key)["Item"]) == current_item

    # Update item to add a num value to a num set
    table.update_item(
        Key=item_key,
        UpdateExpression="ADD num_set :v",
        ExpressionAttributeValues={":v": {6}},
    )
    current_item["num_set"] = current_item["num_set"].union({6})
    assert dict(table.get_item(Key=item_key)["Item"]) == current_item

    # Update item to add a value to a number value
    table.update_item(
        Key=item_key,
        UpdateExpression="ADD num_val :v",
        ExpressionAttributeValues={":v": 20},
    )
    current_item["num_val"] = current_item["num_val"] + 20
    assert dict(table.get_item(Key=item_key)["Item"]) == current_item

    # Attempt to add a number value to a string set, should raise Client Error
    table.update_item.when.called_with(
        Key=item_key,
        UpdateExpression="ADD str_set :v",
        ExpressionAttributeValues={":v": 20},
    ).should.have.raised(ClientError)
    assert dict(table.get_item(Key=item_key)["Item"]) == current_item

    # Attempt to add a number set to the string set, should raise a ClientError
    table.update_item.when.called_with(
        Key=item_key,
        UpdateExpression="ADD str_set :v",
        ExpressionAttributeValues={":v": {20}},
    ).should.have.raised(ClientError)
    assert dict(table.get_item(Key=item_key)["Item"]) == current_item

    # Attempt to update with a bad expression
    table.update_item.when.called_with(
        Key=item_key, UpdateExpression="ADD str_set bad_value"
    ).should.have.raised(ClientError)

    # Attempt to add a string value instead of a string set
    table.update_item.when.called_with(
        Key=item_key,
        UpdateExpression="ADD str_set :v",
        ExpressionAttributeValues={":v": "new_string"},
    ).should.have.raised(ClientError)


@mock_dynamodb2
def test_update_item_add_with_nested_sets():
    table = _create_table_with_range_key()

    item_key = {"forum_name": "the-key", "subject": "123"}
    current_item = {
        "forum_name": "the-key",
        "subject": "123",
        "nested": {"str_set": {"item1", "item2", "item3"}},
    }

    # Put an entry in the DB to play with
    table.put_item(Item=current_item)

    # Update item to add a string value to a nested string set
    table.update_item(
        Key=item_key,
        UpdateExpression="ADD nested.str_set :v",
        ExpressionAttributeValues={":v": {"item4"}},
    )
    current_item["nested"]["str_set"] = current_item["nested"]["str_set"].union(
        {"item4"}
    )
    assert dict(table.get_item(Key=item_key)["Item"]) == current_item

    # Update item to add a string value to a non-existing set
    # Should raise
    table.update_item(
        Key=item_key,
        UpdateExpression="ADD #ns.#ne :v",
        ExpressionAttributeNames={"#ns": "nested", "#ne": "non_existing_str_set"},
        ExpressionAttributeValues={":v": {"new_item"}},
    )
    current_item["nested"]["non_existing_str_set"] = {"new_item"}
    assert dict(table.get_item(Key=item_key)["Item"]) == current_item


@mock_dynamodb2
def test_update_item_delete_with_nested_sets():
    table = _create_table_with_range_key()

    item_key = {"forum_name": "the-key", "subject": "123"}
    current_item = {
        "forum_name": "the-key",
        "subject": "123",
        "nested": {"str_set": {"item1", "item2", "item3"}},
    }

    # Put an entry in the DB to play with
    table.put_item(Item=current_item)

    # Update item to add a string value to a nested string set
    table.update_item(
        Key=item_key,
        UpdateExpression="DELETE nested.str_set :v",
        ExpressionAttributeValues={":v": {"item3"}},
    )
    current_item["nested"]["str_set"] = current_item["nested"]["str_set"].difference(
        {"item3"}
    )
    dict(table.get_item(Key=item_key)["Item"]).should.equal(current_item)


@mock_dynamodb2
def test_update_item_delete_with_expression():
    table = _create_table_with_range_key()

    item_key = {"forum_name": "the-key", "subject": "123"}
    current_item = {
        "forum_name": "the-key",
        "subject": "123",
        "str_set": {"item1", "item2", "item3"},
        "num_set": {1, 2, 3},
        "num_val": 6,
    }

    # Put an entry in the DB to play with
    table.put_item(Item=current_item)

    # Update item to delete a string value from a string set
    table.update_item(
        Key=item_key,
        UpdateExpression="DELETE str_set :v",
        ExpressionAttributeValues={":v": {"item2"}},
    )
    current_item["str_set"] = current_item["str_set"].difference({"item2"})
    dict(table.get_item(Key=item_key)["Item"]).should.equal(current_item)

    # Update item to delete  a num value from a num set
    table.update_item(
        Key=item_key,
        UpdateExpression="DELETE num_set :v",
        ExpressionAttributeValues={":v": {2}},
    )
    current_item["num_set"] = current_item["num_set"].difference({2})
    dict(table.get_item(Key=item_key)["Item"]).should.equal(current_item)

    # Try to delete on a number, this should fail
    table.update_item.when.called_with(
        Key=item_key,
        UpdateExpression="DELETE num_val :v",
        ExpressionAttributeValues={":v": 20},
    ).should.have.raised(ClientError)
    dict(table.get_item(Key=item_key)["Item"]).should.equal(current_item)

    # Try to delete a string set from a number set
    table.update_item.when.called_with(
        Key=item_key,
        UpdateExpression="DELETE num_set :v",
        ExpressionAttributeValues={":v": {"del_str"}},
    ).should.have.raised(ClientError)
    dict(table.get_item(Key=item_key)["Item"]).should.equal(current_item)

    # Attempt to update with a bad expression
    table.update_item.when.called_with(
        Key=item_key, UpdateExpression="DELETE num_val badvalue"
    ).should.have.raised(ClientError)


@mock_dynamodb2
def test_boto3_query_gsi_range_comparison():
    table = _create_table_with_range_key()

    table.put_item(
        Item={
            "forum_name": "the-key",
            "subject": "123",
            "username": "johndoe",
            "created": 3,
        }
    )
    table.put_item(
        Item={
            "forum_name": "the-key",
            "subject": "456",
            "username": "johndoe",
            "created": 1,
        }
    )
    table.put_item(
        Item={
            "forum_name": "the-key",
            "subject": "789",
            "username": "johndoe",
            "created": 2,
        }
    )
    table.put_item(
        Item={
            "forum_name": "the-key",
            "subject": "159",
            "username": "janedoe",
            "created": 2,
        }
    )
    table.put_item(
        Item={
            "forum_name": "the-key",
            "subject": "601",
            "username": "janedoe",
            "created": 5,
        }
    )

    # Test a query returning all johndoe items
    results = table.query(
        KeyConditionExpression=Key("username").eq("johndoe") & Key("created").gt(0),
        ScanIndexForward=True,
        IndexName="TestGSI",
    )
    expected = ["456", "789", "123"]
    for index, item in enumerate(results["Items"]):
        item["subject"].should.equal(expected[index])

    # Return all johndoe items again, but in reverse
    results = table.query(
        KeyConditionExpression=Key("username").eq("johndoe") & Key("created").gt(0),
        ScanIndexForward=False,
        IndexName="TestGSI",
    )
    for index, item in enumerate(reversed(results["Items"])):
        item["subject"].should.equal(expected[index])

    # Filter the creation to only return some of the results
    # And reverse order of hash + range key
    results = table.query(
        KeyConditionExpression=Key("created").gt(1) & Key("username").eq("johndoe"),
        ConsistentRead=True,
        IndexName="TestGSI",
    )
    results["Count"].should.equal(2)

    # Filter to return no results
    results = table.query(
        KeyConditionExpression=Key("username").eq("janedoe") & Key("created").gt(9),
        IndexName="TestGSI",
    )
    results["Count"].should.equal(0)

    results = table.query(
        KeyConditionExpression=Key("username").eq("janedoe") & Key("created").eq(5),
        IndexName="TestGSI",
    )
    results["Count"].should.equal(1)

    # Test range key sorting
    results = table.query(
        KeyConditionExpression=Key("username").eq("johndoe") & Key("created").gt(0),
        IndexName="TestGSI",
    )
    expected = [Decimal("1"), Decimal("2"), Decimal("3")]
    for index, item in enumerate(results["Items"]):
        item["created"].should.equal(expected[index])


@mock_dynamodb2
def test_boto3_update_table_throughput():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 6},
    )
    table = dynamodb.Table("users")

    table.provisioned_throughput["ReadCapacityUnits"].should.equal(5)
    table.provisioned_throughput["WriteCapacityUnits"].should.equal(6)

    table.update(
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 11}
    )

    table = dynamodb.Table("users")

    table.provisioned_throughput["ReadCapacityUnits"].should.equal(10)
    table.provisioned_throughput["WriteCapacityUnits"].should.equal(11)


@mock_dynamodb2
def test_boto3_update_table_gsi_throughput():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "TestGSI",
                "KeySchema": [
                    {"AttributeName": "username", "KeyType": "HASH"},
                    {"AttributeName": "created", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 3,
                    "WriteCapacityUnits": 4,
                },
            }
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
            {"AttributeName": "username", "AttributeType": "S"},
            {"AttributeName": "created", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 6},
    )
    table = dynamodb.Table("users")

    gsi_throughput = table.global_secondary_indexes[0]["ProvisionedThroughput"]
    gsi_throughput["ReadCapacityUnits"].should.equal(3)
    gsi_throughput["WriteCapacityUnits"].should.equal(4)

    table.provisioned_throughput["ReadCapacityUnits"].should.equal(5)
    table.provisioned_throughput["WriteCapacityUnits"].should.equal(6)

    table.update(
        GlobalSecondaryIndexUpdates=[
            {
                "Update": {
                    "IndexName": "TestGSI",
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 10,
                        "WriteCapacityUnits": 11,
                    },
                }
            }
        ]
    )

    table = dynamodb.Table("users")

    # Primary throughput has not changed
    table.provisioned_throughput["ReadCapacityUnits"].should.equal(5)
    table.provisioned_throughput["WriteCapacityUnits"].should.equal(6)

    gsi_throughput = table.global_secondary_indexes[0]["ProvisionedThroughput"]
    gsi_throughput["ReadCapacityUnits"].should.equal(10)
    gsi_throughput["WriteCapacityUnits"].should.equal(11)


@mock_dynamodb2
def test_update_table_gsi_create():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 6},
    )
    table = dynamodb.Table("users")

    table.global_secondary_indexes.should.have.length_of(0)

    table.update(
        GlobalSecondaryIndexUpdates=[
            {
                "Create": {
                    "IndexName": "TestGSI",
                    "KeySchema": [
                        {"AttributeName": "username", "KeyType": "HASH"},
                        {"AttributeName": "created", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 3,
                        "WriteCapacityUnits": 4,
                    },
                }
            }
        ]
    )

    table = dynamodb.Table("users")
    table.global_secondary_indexes.should.have.length_of(1)

    gsi_throughput = table.global_secondary_indexes[0]["ProvisionedThroughput"]
    assert gsi_throughput["ReadCapacityUnits"].should.equal(3)
    assert gsi_throughput["WriteCapacityUnits"].should.equal(4)

    # Check update works
    table.update(
        GlobalSecondaryIndexUpdates=[
            {
                "Update": {
                    "IndexName": "TestGSI",
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits": 10,
                        "WriteCapacityUnits": 11,
                    },
                }
            }
        ]
    )
    table = dynamodb.Table("users")

    gsi_throughput = table.global_secondary_indexes[0]["ProvisionedThroughput"]
    assert gsi_throughput["ReadCapacityUnits"].should.equal(10)
    assert gsi_throughput["WriteCapacityUnits"].should.equal(11)

    table.update(GlobalSecondaryIndexUpdates=[{"Delete": {"IndexName": "TestGSI"}}])

    table = dynamodb.Table("users")
    table.global_secondary_indexes.should.have.length_of(0)


@mock_dynamodb2
def test_update_table_gsi_throughput():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName="users",
        KeySchema=[
            {"AttributeName": "forum_name", "KeyType": "HASH"},
            {"AttributeName": "subject", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "TestGSI",
                "KeySchema": [
                    {"AttributeName": "username", "KeyType": "HASH"},
                    {"AttributeName": "created", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 3,
                    "WriteCapacityUnits": 4,
                },
            }
        ],
        AttributeDefinitions=[
            {"AttributeName": "forum_name", "AttributeType": "S"},
            {"AttributeName": "subject", "AttributeType": "S"},
            {"AttributeName": "username", "AttributeType": "S"},
            {"AttributeName": "created", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 6},
    )
    table = dynamodb.Table("users")
    table.global_secondary_indexes.should.have.length_of(1)

    table.update(GlobalSecondaryIndexUpdates=[{"Delete": {"IndexName": "TestGSI"}}])

    table = dynamodb.Table("users")
    table.global_secondary_indexes.should.have.length_of(0)


@mock_dynamodb2
def test_query_pagination():
    table = _create_table_with_range_key()
    for i in range(10):
        table.put_item(
            Item={
                "forum_name": "the-key",
                "subject": "{0}".format(i),
                "username": "johndoe",
                "created": Decimal("3"),
            }
        )

    page1 = table.query(KeyConditionExpression=Key("forum_name").eq("the-key"), Limit=6)
    page1["Count"].should.equal(6)
    page1["Items"].should.have.length_of(6)
    page1.should.have.key("LastEvaluatedKey")

    page2 = table.query(
        KeyConditionExpression=Key("forum_name").eq("the-key"),
        Limit=6,
        ExclusiveStartKey=page1["LastEvaluatedKey"],
    )
    page2["Count"].should.equal(4)
    page2["Items"].should.have.length_of(4)
    page2.should_not.have.key("LastEvaluatedKey")

    results = page1["Items"] + page2["Items"]
    subjects = set([int(r["subject"]) for r in results])
    subjects.should.equal(set(range(10)))


@mock_dynamodb2
def test_scan_by_index():
    dynamodb = boto3.client("dynamodb", region_name="us-east-1")

    dynamodb.create_table(
        TableName="test",
        KeySchema=[
            {"AttributeName": "id", "KeyType": "HASH"},
            {"AttributeName": "range_key", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "range_key", "AttributeType": "S"},
            {"AttributeName": "gsi_col", "AttributeType": "S"},
            {"AttributeName": "gsi_range_key", "AttributeType": "S"},
            {"AttributeName": "lsi_range_key", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "test_gsi",
                "KeySchema": [
                    {"AttributeName": "gsi_col", "KeyType": "HASH"},
                    {"AttributeName": "gsi_range_key", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
        LocalSecondaryIndexes=[
            {
                "IndexName": "test_lsi",
                "KeySchema": [
                    {"AttributeName": "id", "KeyType": "HASH"},
                    {"AttributeName": "lsi_range_key", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )

    dynamodb.put_item(
        TableName="test",
        Item={
            "id": {"S": "1"},
            "range_key": {"S": "1"},
            "col1": {"S": "val1"},
            "gsi_col": {"S": "1"},
            "gsi_range_key": {"S": "1"},
            "lsi_range_key": {"S": "1"},
        },
    )

    dynamodb.put_item(
        TableName="test",
        Item={
            "id": {"S": "1"},
            "range_key": {"S": "2"},
            "col1": {"S": "val2"},
            "gsi_col": {"S": "1"},
            "gsi_range_key": {"S": "2"},
            "lsi_range_key": {"S": "2"},
        },
    )

    dynamodb.put_item(
        TableName="test",
        Item={"id": {"S": "3"}, "range_key": {"S": "1"}, "col1": {"S": "val3"}},
    )

    res = dynamodb.scan(TableName="test")
    assert res["Count"] == 3
    assert len(res["Items"]) == 3

    res = dynamodb.scan(TableName="test", IndexName="test_gsi")
    assert res["Count"] == 2
    assert len(res["Items"]) == 2

    res = dynamodb.scan(TableName="test", IndexName="test_gsi", Limit=1)
    assert res["Count"] == 1
    assert len(res["Items"]) == 1
    last_eval_key = res["LastEvaluatedKey"]
    assert last_eval_key["id"]["S"] == "1"
    assert last_eval_key["gsi_col"]["S"] == "1"
    assert last_eval_key["gsi_range_key"]["S"] == "1"

    res = dynamodb.scan(TableName="test", IndexName="test_lsi")
    assert res["Count"] == 2
    assert len(res["Items"]) == 2

    res = dynamodb.scan(TableName="test", IndexName="test_lsi", Limit=1)
    assert res["Count"] == 1
    assert len(res["Items"]) == 1
    last_eval_key = res["LastEvaluatedKey"]
    assert last_eval_key["id"]["S"] == "1"
    assert last_eval_key["range_key"]["S"] == "1"
    assert last_eval_key["lsi_range_key"]["S"] == "1"
