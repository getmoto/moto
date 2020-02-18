from __future__ import unicode_literals

import boto
import sure  # noqa
from freezegun import freeze_time

from moto import mock_dynamodb_deprecated

from boto.dynamodb import condition
from boto.dynamodb.exceptions import DynamoDBKeyNotFoundError
from boto.exception import DynamoDBResponseError


def create_table(conn):
    message_table_schema = conn.create_schema(
        hash_key_name="forum_name", hash_key_proto_value=str
    )

    table = conn.create_table(
        name="messages", schema=message_table_schema, read_units=10, write_units=10
    )
    return table


@freeze_time("2012-01-14")
@mock_dynamodb_deprecated
def test_create_table():
    conn = boto.connect_dynamodb()
    create_table(conn)

    expected = {
        "Table": {
            "CreationDateTime": 1326499200.0,
            "ItemCount": 0,
            "KeySchema": {
                "HashKeyElement": {"AttributeName": "forum_name", "AttributeType": "S"}
            },
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 10,
                "WriteCapacityUnits": 10,
            },
            "TableName": "messages",
            "TableSizeBytes": 0,
            "TableStatus": "ACTIVE",
        }
    }
    conn.describe_table("messages").should.equal(expected)


@mock_dynamodb_deprecated
def test_delete_table():
    conn = boto.connect_dynamodb()
    create_table(conn)
    conn.list_tables().should.have.length_of(1)

    conn.layer1.delete_table("messages")
    conn.list_tables().should.have.length_of(0)

    conn.layer1.delete_table.when.called_with("messages").should.throw(
        DynamoDBResponseError
    )


@mock_dynamodb_deprecated
def test_update_table_throughput():
    conn = boto.connect_dynamodb()
    table = create_table(conn)
    table.read_units.should.equal(10)
    table.write_units.should.equal(10)

    table.update_throughput(5, 6)
    table.refresh()

    table.read_units.should.equal(5)
    table.write_units.should.equal(6)


@mock_dynamodb_deprecated
def test_item_add_and_describe_and_update():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(hash_key="LOLCat Forum", attrs=item_data)
    item.put()

    returned_item = table.get_item(
        hash_key="LOLCat Forum", attributes_to_get=["Body", "SentBy"]
    )
    dict(returned_item).should.equal(
        {
            "forum_name": "LOLCat Forum",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User A",
        }
    )

    item["SentBy"] = "User B"
    item.put()

    returned_item = table.get_item(
        hash_key="LOLCat Forum", attributes_to_get=["Body", "SentBy"]
    )
    dict(returned_item).should.equal(
        {
            "forum_name": "LOLCat Forum",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User B",
        }
    )


@mock_dynamodb_deprecated
def test_item_put_without_table():
    conn = boto.connect_dynamodb()

    conn.layer1.put_item.when.called_with(
        table_name="undeclared-table", item=dict(hash_key="LOLCat Forum")
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb_deprecated
def test_get_missing_item():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    table.get_item.when.called_with(hash_key="tester").should.throw(
        DynamoDBKeyNotFoundError
    )


@mock_dynamodb_deprecated
def test_get_item_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.get_item.when.called_with(
        table_name="undeclared-table", key={"HashKeyElement": {"S": "tester"}}
    ).should.throw(DynamoDBKeyNotFoundError)


@mock_dynamodb_deprecated
def test_delete_item():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(hash_key="LOLCat Forum", attrs=item_data)
    item.put()

    table.refresh()
    table.item_count.should.equal(1)

    response = item.delete()
    response.should.equal({"Attributes": [], "ConsumedCapacityUnits": 0.5})
    table.refresh()
    table.item_count.should.equal(0)

    item.delete.when.called_with().should.throw(DynamoDBResponseError)


@mock_dynamodb_deprecated
def test_delete_item_with_attribute_response():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(hash_key="LOLCat Forum", attrs=item_data)
    item.put()

    table.refresh()
    table.item_count.should.equal(1)

    response = item.delete(return_values="ALL_OLD")
    response.should.equal(
        {
            "Attributes": {
                "Body": "http://url_to_lolcat.gif",
                "forum_name": "LOLCat Forum",
                "ReceivedTime": "12/9/2011 11:36:03 PM",
                "SentBy": "User A",
            },
            "ConsumedCapacityUnits": 0.5,
        }
    )
    table.refresh()
    table.item_count.should.equal(0)

    item.delete.when.called_with().should.throw(DynamoDBResponseError)


@mock_dynamodb_deprecated
def test_delete_item_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.delete_item.when.called_with(
        table_name="undeclared-table", key={"HashKeyElement": {"S": "tester"}}
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb_deprecated
def test_query():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(hash_key="the-key", attrs=item_data)
    item.put()

    results = table.query(hash_key="the-key")
    results.response["Items"].should.have.length_of(1)


@mock_dynamodb_deprecated
def test_query_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.query.when.called_with(
        table_name="undeclared-table", hash_key_value={"S": "the-key"}
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb_deprecated
def test_scan():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(hash_key="the-key", attrs=item_data)
    item.put()

    item = table.new_item(hash_key="the-key2", attrs=item_data)
    item.put()

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User B",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
        "Ids": set([1, 2, 3]),
        "PK": 7,
    }
    item = table.new_item(hash_key="the-key3", attrs=item_data)
    item.put()

    results = table.scan()
    results.response["Items"].should.have.length_of(3)

    results = table.scan(scan_filter={"SentBy": condition.EQ("User B")})
    results.response["Items"].should.have.length_of(1)

    results = table.scan(scan_filter={"Body": condition.BEGINS_WITH("http")})
    results.response["Items"].should.have.length_of(3)

    results = table.scan(scan_filter={"Ids": condition.CONTAINS(2)})
    results.response["Items"].should.have.length_of(1)

    results = table.scan(scan_filter={"Ids": condition.NOT_NULL()})
    results.response["Items"].should.have.length_of(1)

    results = table.scan(scan_filter={"Ids": condition.NULL()})
    results.response["Items"].should.have.length_of(2)

    results = table.scan(scan_filter={"PK": condition.BETWEEN(8, 9)})
    results.response["Items"].should.have.length_of(0)

    results = table.scan(scan_filter={"PK": condition.BETWEEN(5, 8)})
    results.response["Items"].should.have.length_of(1)


@mock_dynamodb_deprecated
def test_scan_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.scan.when.called_with(
        table_name="undeclared-table",
        scan_filter={
            "SentBy": {
                "AttributeValueList": [{"S": "User B"}],
                "ComparisonOperator": "EQ",
            }
        },
    ).should.throw(DynamoDBResponseError)


@mock_dynamodb_deprecated
def test_scan_after_has_item():
    conn = boto.connect_dynamodb()
    table = create_table(conn)
    list(table.scan()).should.equal([])

    table.has_item("the-key")

    list(table.scan()).should.equal([])


@mock_dynamodb_deprecated
def test_write_batch():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    batch_list = conn.new_batch_write_list()

    items = []
    items.append(
        table.new_item(
            hash_key="the-key",
            attrs={
                "Body": "http://url_to_lolcat.gif",
                "SentBy": "User A",
                "ReceivedTime": "12/9/2011 11:36:03 PM",
            },
        )
    )

    items.append(
        table.new_item(
            hash_key="the-key2",
            attrs={
                "Body": "http://url_to_lolcat.gif",
                "SentBy": "User B",
                "ReceivedTime": "12/9/2011 11:36:03 PM",
                "Ids": set([1, 2, 3]),
                "PK": 7,
            },
        )
    )

    batch_list.add_batch(table, puts=items)
    conn.batch_write_item(batch_list)

    table.refresh()
    table.item_count.should.equal(2)

    batch_list = conn.new_batch_write_list()
    batch_list.add_batch(table, deletes=[("the-key")])
    conn.batch_write_item(batch_list)

    table.refresh()
    table.item_count.should.equal(1)


@mock_dynamodb_deprecated
def test_batch_read():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(hash_key="the-key1", attrs=item_data)
    item.put()

    item = table.new_item(hash_key="the-key2", attrs=item_data)
    item.put()

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User B",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
        "Ids": set([1, 2, 3]),
        "PK": 7,
    }
    item = table.new_item(hash_key="another-key", attrs=item_data)
    item.put()

    items = table.batch_get_item([("the-key1"), ("another-key")])
    # Iterate through so that batch_item gets called
    count = len([x for x in items])
    count.should.have.equal(2)
