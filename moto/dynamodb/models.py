from __future__ import unicode_literals
from collections import defaultdict
import datetime
import json

from collections import OrderedDict
from moto.core import BaseBackend, BaseModel, CloudFormationModel
from moto.core.utils import unix_time
from moto.core import ACCOUNT_ID
from .comparisons import get_comparison_func


class DynamoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_json"):
            return obj.to_json()


def dynamo_json_dump(dynamo_object):
    return json.dumps(dynamo_object, cls=DynamoJsonEncoder)


class DynamoType(object):
    """
    http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DataModel.html#DataModelDataTypes
    """

    def __init__(self, type_as_dict):
        self.type = list(type_as_dict.keys())[0]
        self.value = list(type_as_dict.values())[0]

    def __hash__(self):
        return hash((self.type, self.value))

    def __eq__(self, other):
        return self.type == other.type and self.value == other.value

    def __repr__(self):
        return "DynamoType: {0}".format(self.to_json())

    def to_json(self):
        return {self.type: self.value}

    def compare(self, range_comparison, range_objs):
        """
        Compares this type against comparison filters
        """
        range_values = [obj.value for obj in range_objs]
        comparison_func = get_comparison_func(range_comparison)
        return comparison_func(self.value, *range_values)


class Item(BaseModel):
    def __init__(self, hash_key, hash_key_type, range_key, range_key_type, attrs):
        self.hash_key = hash_key
        self.hash_key_type = hash_key_type
        self.range_key = range_key
        self.range_key_type = range_key_type

        self.attrs = {}
        for key, value in attrs.items():
            self.attrs[key] = DynamoType(value)

    def __repr__(self):
        return "Item: {0}".format(self.to_json())

    def to_json(self):
        attributes = {}
        for attribute_key, attribute in self.attrs.items():
            attributes[attribute_key] = attribute.value

        return {"Attributes": attributes}

    def describe_attrs(self, attributes):
        if attributes:
            included = {}
            for key, value in self.attrs.items():
                if key in attributes:
                    included[key] = value
        else:
            included = self.attrs
        return {"Item": included}


class Table(CloudFormationModel):
    def __init__(
        self,
        name,
        hash_key_attr,
        hash_key_type,
        range_key_attr=None,
        range_key_type=None,
        read_capacity=None,
        write_capacity=None,
    ):
        self.name = name
        self.hash_key_attr = hash_key_attr
        self.hash_key_type = hash_key_type
        self.range_key_attr = range_key_attr
        self.range_key_type = range_key_type
        self.read_capacity = read_capacity
        self.write_capacity = write_capacity
        self.created_at = datetime.datetime.utcnow()
        self.items = defaultdict(dict)

    @property
    def has_range_key(self):
        return self.range_key_attr is not None

    @property
    def describe(self):
        results = {
            "Table": {
                "CreationDateTime": unix_time(self.created_at),
                "KeySchema": {
                    "HashKeyElement": {
                        "AttributeName": self.hash_key_attr,
                        "AttributeType": self.hash_key_type,
                    }
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": self.read_capacity,
                    "WriteCapacityUnits": self.write_capacity,
                },
                "TableName": self.name,
                "TableStatus": "ACTIVE",
                "ItemCount": len(self),
                "TableSizeBytes": 0,
            }
        }
        if self.has_range_key:
            results["Table"]["KeySchema"]["RangeKeyElement"] = {
                "AttributeName": self.range_key_attr,
                "AttributeType": self.range_key_type,
            }
        return results

    @staticmethod
    def cloudformation_name_type():
        return "TableName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dynamodb-table.html
        return "AWS::DynamoDB::Table"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        key_attr = [
            i["AttributeName"]
            for i in properties["KeySchema"]
            if i["KeyType"] == "HASH"
        ][0]
        key_type = [
            i["AttributeType"]
            for i in properties["AttributeDefinitions"]
            if i["AttributeName"] == key_attr
        ][0]
        spec = {
            "name": properties["TableName"],
            "hash_key_attr": key_attr,
            "hash_key_type": key_type,
        }
        # TODO: optional properties still missing:
        # range_key_attr, range_key_type, read_capacity, write_capacity
        return Table(**spec)

    def __len__(self):
        count = 0
        for key, value in self.items.items():
            if self.has_range_key:
                count += len(value)
            else:
                count += 1
        return count

    def __nonzero__(self):
        return True

    def __bool__(self):
        return self.__nonzero__()

    def put_item(self, item_attrs):
        hash_value = DynamoType(item_attrs.get(self.hash_key_attr))
        if self.has_range_key:
            range_value = DynamoType(item_attrs.get(self.range_key_attr))
        else:
            range_value = None

        item = Item(
            hash_value, self.hash_key_type, range_value, self.range_key_type, item_attrs
        )

        if range_value:
            self.items[hash_value][range_value] = item
        else:
            self.items[hash_value] = item
        return item

    def get_item(self, hash_key, range_key):
        if self.has_range_key and not range_key:
            raise ValueError(
                "Table has a range key, but no range key was passed into get_item"
            )
        try:
            if range_key:
                return self.items[hash_key][range_key]
            else:
                return self.items[hash_key]
        except KeyError:
            return None

    def query(self, hash_key, range_comparison, range_objs):
        results = []
        last_page = True  # Once pagination is implemented, change this

        if self.range_key_attr:
            possible_results = self.items[hash_key].values()
        else:
            possible_results = list(self.all_items())

        if range_comparison:
            for result in possible_results:
                if result.range_key.compare(range_comparison, range_objs):
                    results.append(result)
        else:
            # If we're not filtering on range key, return all values
            results = possible_results
        return results, last_page

    def all_items(self):
        for hash_set in self.items.values():
            if self.range_key_attr:
                for item in hash_set.values():
                    yield item
            else:
                yield hash_set

    def scan(self, filters):
        results = []
        scanned_count = 0
        last_page = True  # Once pagination is implemented, change this

        for result in self.all_items():
            scanned_count += 1
            passes_all_conditions = True
            for (
                attribute_name,
                (comparison_operator, comparison_objs),
            ) in filters.items():
                attribute = result.attrs.get(attribute_name)

                if attribute:
                    # Attribute found
                    if not attribute.compare(comparison_operator, comparison_objs):
                        passes_all_conditions = False
                        break
                elif comparison_operator == "NULL":
                    # Comparison is NULL and we don't have the attribute
                    continue
                else:
                    # No attribute found and comparison is no NULL. This item
                    # fails
                    passes_all_conditions = False
                    break

            if passes_all_conditions:
                results.append(result)

        return results, scanned_count, last_page

    def delete_item(self, hash_key, range_key):
        try:
            if range_key:
                return self.items[hash_key].pop(range_key)
            else:
                return self.items.pop(hash_key)
        except KeyError:
            return None

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "StreamArn":
            region = "us-east-1"
            time = "2000-01-01T00:00:00.000"
            return "arn:aws:dynamodb:{0}:{1}:table/{2}/stream/{3}".format(
                region, ACCOUNT_ID, self.name, time
            )
        raise UnformattedGetAttTemplateException()


class DynamoDBBackend(BaseBackend):
    def __init__(self):
        self.tables = OrderedDict()

    def create_table(self, name, **params):
        table = Table(name, **params)
        self.tables[name] = table
        return table

    def delete_table(self, name):
        return self.tables.pop(name, None)

    def update_table_throughput(self, name, new_read_units, new_write_units):
        table = self.tables[name]
        table.read_capacity = new_read_units
        table.write_capacity = new_write_units
        return table

    def put_item(self, table_name, item_attrs):
        table = self.tables.get(table_name)
        if not table:
            return None

        return table.put_item(item_attrs)

    def get_item(self, table_name, hash_key_dict, range_key_dict):
        table = self.tables.get(table_name)
        if not table:
            return None

        hash_key = DynamoType(hash_key_dict)
        range_key = DynamoType(range_key_dict) if range_key_dict else None

        return table.get_item(hash_key, range_key)

    def query(self, table_name, hash_key_dict, range_comparison, range_value_dicts):
        table = self.tables.get(table_name)
        if not table:
            return None, None

        hash_key = DynamoType(hash_key_dict)
        range_values = [DynamoType(range_value) for range_value in range_value_dicts]

        return table.query(hash_key, range_comparison, range_values)

    def scan(self, table_name, filters):
        table = self.tables.get(table_name)
        if not table:
            return None, None, None

        scan_filters = {}
        for key, (comparison_operator, comparison_values) in filters.items():
            dynamo_types = [DynamoType(value) for value in comparison_values]
            scan_filters[key] = (comparison_operator, dynamo_types)

        return table.scan(scan_filters)

    def delete_item(self, table_name, hash_key_dict, range_key_dict):
        table = self.tables.get(table_name)
        if not table:
            return None

        hash_key = DynamoType(hash_key_dict)
        range_key = DynamoType(range_key_dict) if range_key_dict else None

        return table.delete_item(hash_key, range_key)


dynamodb_backend = DynamoDBBackend()
