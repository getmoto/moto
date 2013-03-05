import datetime

from moto.core import BaseBackend
from .utils import unix_time


class Table(object):

    def __init__(self, name, hash_key_attr=None, hash_key_type=None,
                 range_key_attr=None, range_key_type=None, read_capacity=None,
                 write_capacity=None):
        self.name = name
        self.hash_key_attr = hash_key_attr
        self.hash_key_type = hash_key_type
        self.range_key_attr = range_key_attr
        self.range_key_type = range_key_type
        self.read_capacity = read_capacity
        self.write_capacity = write_capacity
        self.created_at = datetime.datetime.now()

    @property
    def describe(self):
        return {
            "Table": {
                "CreationDateTime": unix_time(self.created_at),
                "KeySchema": {
                    "HashKeyElement": {
                        "AttributeName": self.hash_key_attr,
                        "AttributeType": self.hash_key_type
                    },
                    "RangeKeyElement": {
                        "AttributeName": self.range_key_attr,
                        "AttributeType": self.range_key_type
                    }
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": self.read_capacity,
                    "WriteCapacityUnits": self.write_capacity
                },
                "TableName": self.name,
                "TableStatus": "ACTIVE",
                "ItemCount": 0,
                "TableSizeBytes": 0,
            }
        }


class DynamoDBBackend(BaseBackend):

    def __init__(self):
        self.tables = {}

    def create_table(self, name, **params):
        self.tables[name] = Table(name, **params)

dynamodb_backend = DynamoDBBackend()
