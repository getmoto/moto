import boto
import sure  # noqa # pylint: disable=unused-import
from freezegun import freeze_time

from moto import mock_dynamodb_deprecated

from boto.dynamodb import condition
from boto.dynamodb.exceptions import DynamoDBKeyNotFoundError, DynamoDBValidationError
from boto.exception import DynamoDBResponseError


def create_table(conn):
    message_table_schema = conn.create_schema(
        hash_key_name="forum_name",
        hash_key_proto_value=str,
        range_key_name="subject",
        range_key_proto_value=str,
    )

    table = conn.create_table(
        name="messages", schema=message_table_schema, read_units=10, write_units=10
    )
    return table


# Has boto3 equivalent
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
                "HashKeyElement": {"AttributeName": "forum_name", "AttributeType": "S"},
                "RangeKeyElement": {"AttributeName": "subject", "AttributeType": "S"},
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


# Has boto3 equivalent
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


# Has boto3 equivalent
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


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_item_add_and_describe_and_update():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(
        hash_key="LOLCat Forum", range_key="Check this out!", attrs=item_data
    )
    item.put()

    table.has_item("LOLCat Forum", "Check this out!").should.equal(True)

    returned_item = table.get_item(
        hash_key="LOLCat Forum",
        range_key="Check this out!",
        attributes_to_get=["Body", "SentBy"],
    )
    dict(returned_item).should.equal(
        {
            "forum_name": "LOLCat Forum",
            "subject": "Check this out!",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User A",
        }
    )

    item["SentBy"] = "User B"
    item.put()

    returned_item = table.get_item(
        hash_key="LOLCat Forum",
        range_key="Check this out!",
        attributes_to_get=["Body", "SentBy"],
    )
    dict(returned_item).should.equal(
        {
            "forum_name": "LOLCat Forum",
            "subject": "Check this out!",
            "Body": "http://url_to_lolcat.gif",
            "SentBy": "User B",
        }
    )


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_item_put_without_table():
    conn = boto.connect_dynamodb()

    conn.layer1.put_item.when.called_with(
        table_name="undeclared-table",
        item=dict(hash_key="LOLCat Forum", range_key="Check this out!"),
    ).should.throw(DynamoDBResponseError)


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_get_missing_item():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    table.get_item.when.called_with(hash_key="tester", range_key="other").should.throw(
        DynamoDBKeyNotFoundError
    )
    table.has_item("foobar", "more").should.equal(False)


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_get_item_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.get_item.when.called_with(
        table_name="undeclared-table",
        key={"HashKeyElement": {"S": "tester"}, "RangeKeyElement": {"S": "test-range"}},
    ).should.throw(DynamoDBKeyNotFoundError)


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_get_item_without_range_key():
    conn = boto.connect_dynamodb()
    message_table_schema = conn.create_schema(
        hash_key_name="test_hash",
        hash_key_proto_value=int,
        range_key_name="test_range",
        range_key_proto_value=int,
    )
    table = conn.create_table(
        name="messages", schema=message_table_schema, read_units=10, write_units=10
    )

    hash_key = 3241526475
    range_key = 1234567890987
    new_item = table.new_item(hash_key=hash_key, range_key=range_key)
    new_item.put()

    table.get_item.when.called_with(hash_key=hash_key).should.throw(
        DynamoDBValidationError
    )


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_delete_item():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(
        hash_key="LOLCat Forum", range_key="Check this out!", attrs=item_data
    )
    item.put()

    table.refresh()
    table.item_count.should.equal(1)

    response = item.delete()
    response.should.equal({"Attributes": [], "ConsumedCapacityUnits": 0.5})
    table.refresh()
    table.item_count.should.equal(0)

    item.delete.when.called_with().should.throw(DynamoDBResponseError)


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_delete_item_with_attribute_response():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(
        hash_key="LOLCat Forum", range_key="Check this out!", attrs=item_data
    )
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
                "subject": "Check this out!",
            },
            "ConsumedCapacityUnits": 0.5,
        }
    )
    table.refresh()
    table.item_count.should.equal(0)

    item.delete.when.called_with().should.throw(DynamoDBResponseError)


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_delete_item_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.delete_item.when.called_with(
        table_name="undeclared-table",
        key={"HashKeyElement": {"S": "tester"}, "RangeKeyElement": {"S": "test-range"}},
    ).should.throw(DynamoDBResponseError)


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_query():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(hash_key="the-key", range_key="456", attrs=item_data)
    item.put()

    item = table.new_item(hash_key="the-key", range_key="123", attrs=item_data)
    item.put()

    item = table.new_item(hash_key="the-key", range_key="789", attrs=item_data)
    item.put()

    results = table.query(hash_key="the-key", range_key_condition=condition.GT("1"))
    results.response["Items"].should.have.length_of(3)

    results = table.query(hash_key="the-key", range_key_condition=condition.GT("234"))
    results.response["Items"].should.have.length_of(2)

    results = table.query(hash_key="the-key", range_key_condition=condition.GT("9999"))
    results.response["Items"].should.have.length_of(0)

    results = table.query(
        hash_key="the-key", range_key_condition=condition.CONTAINS("12")
    )
    results.response["Items"].should.have.length_of(1)

    results = table.query(
        hash_key="the-key", range_key_condition=condition.BEGINS_WITH("7")
    )
    results.response["Items"].should.have.length_of(1)

    results = table.query(
        hash_key="the-key", range_key_condition=condition.BETWEEN("567", "890")
    )
    results.response["Items"].should.have.length_of(1)


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_query_with_undeclared_table():
    conn = boto.connect_dynamodb()

    conn.layer1.query.when.called_with(
        table_name="undeclared-table",
        hash_key_value={"S": "the-key"},
        range_key_conditions={
            "AttributeValueList": [{"S": "User B"}],
            "ComparisonOperator": "EQ",
        },
    ).should.throw(DynamoDBResponseError)


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_scan():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(hash_key="the-key", range_key="456", attrs=item_data)
    item.put()

    item = table.new_item(hash_key="the-key", range_key="123", attrs=item_data)
    item.put()

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User B",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
        "Ids": set([1, 2, 3]),
        "PK": 7,
    }
    item = table.new_item(hash_key="the-key", range_key="789", attrs=item_data)
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


# Has boto3 equivalent
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

    table.has_item(hash_key="the-key", range_key="123")

    list(table.scan()).should.equal([])


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_write_batch():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    batch_list = conn.new_batch_write_list()

    items = []
    items.append(
        table.new_item(
            hash_key="the-key",
            range_key="123",
            attrs={
                "Body": "http://url_to_lolcat.gif",
                "SentBy": "User A",
                "ReceivedTime": "12/9/2011 11:36:03 PM",
            },
        )
    )

    items.append(
        table.new_item(
            hash_key="the-key",
            range_key="789",
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
    batch_list.add_batch(table, deletes=[("the-key", "789")])
    conn.batch_write_item(batch_list)

    table.refresh()
    table.item_count.should.equal(1)


# Has boto3 equivalent
@mock_dynamodb_deprecated
def test_batch_read():
    conn = boto.connect_dynamodb()
    table = create_table(conn)

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User A",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
    }
    item = table.new_item(hash_key="the-key", range_key="456", attrs=item_data)
    item.put()

    item = table.new_item(hash_key="the-key", range_key="123", attrs=item_data)
    item.put()

    item_data = {
        "Body": "http://url_to_lolcat.gif",
        "SentBy": "User B",
        "ReceivedTime": "12/9/2011 11:36:03 PM",
        "Ids": set([1, 2, 3]),
        "PK": 7,
    }
    item = table.new_item(hash_key="another-key", range_key="789", attrs=item_data)
    item.put()

    items = table.batch_get_item([("the-key", "123"), ("another-key", "789")])
    # Iterate through so that batch_item gets called
    count = len([x for x in items])
    count.should.equal(2)
