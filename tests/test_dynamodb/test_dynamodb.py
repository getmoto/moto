import boto

from moto import mock_dynamodb
from moto.dynamodb import dynamodb_backend


@mock_dynamodb
def test_list_tables():
    name = "TestTable"
    dynamodb_backend.create_table(name)
    conn = boto.connect_dynamodb('the_key', 'the_secret')
    assert conn.list_tables() == ['TestTable']
