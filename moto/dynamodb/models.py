import datetime

from collections import defaultdict, OrderedDict

from moto.core import BaseBackend
from .comparisons import get_comparison_func
from .utils import unix_time


class Item(object):
    def __init__(self, hash_key, hash_key_type, range_key, range_key_type, attrs):
        self.hash_key = hash_key
        self.hash_key_type = hash_key_type
        self.range_key = range_key
        self.range_key_type = range_key_type
        self.attrs = attrs

    @property
    def describe(self):
        return {
            "Attributes": self.attrs
        }

    def describe_attrs(self, attributes):
        if attributes:
            included = {}
            for key, value in self.attrs.iteritems():
                if key in attributes:
                    included[key] = value
        else:
            included = self.attrs
        return {
            "Item": included
        }


class Table(object):

    def __init__(self, name, hash_key_attr, hash_key_type,
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
        self.items = defaultdict(dict)

    @property
    def describe(self):
        results = {
            "Table": {
                "CreationDateTime": unix_time(self.created_at),
                "KeySchema": {
                    "HashKeyElement": {
                        "AttributeName": self.hash_key_attr,
                        "AttributeType": self.hash_key_type
                    },
                },
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": self.read_capacity,
                    "WriteCapacityUnits": self.write_capacity
                },
                "TableName": self.name,
                "TableStatus": "ACTIVE",
                "ItemCount": len(self),
                "TableSizeBytes": 0,
            }
        }
        if self.range_key_attr:
            results["Table"]["KeySchema"]["RangeKeyElement"] = {
                "AttributeName": self.range_key_attr,
                "AttributeType": self.range_key_type
            }
        return results

    def __len__(self):
        count = 0
        for key, value in self.items.iteritems():
            if self.range_key_attr:
                count += len(value)
            else:
                count += 1
        return count

    def __nonzero__(self):
        return True

    def put_item(self, item_attrs):
        hash_value = item_attrs.get(self.hash_key_attr).values()[0]
        if self.range_key_attr:
            range_value = item_attrs.get(self.range_key_attr).values()[0]
        else:
            range_value = None
        item = Item(hash_value, self.hash_key_type, range_value, self.range_key_type, item_attrs)

        if range_value:
            self.items[hash_value][range_value] = item
        else:
            self.items[hash_value] = item
        return item

    def get_item(self, hash_key, range_key):
        try:
            if range_key:
                return self.items[hash_key][range_key]
            else:
                return self.items[hash_key]
        except KeyError:
            return None

    def query(self, hash_key, range_comparison, range_values):
        results = []
        last_page = True  # Once pagination is implemented, change this

        possible_results = list(self.all_items())
        if range_comparison:
            comparison_func = get_comparison_func(range_comparison)
            for result in possible_results:
                if comparison_func(result.range_key, *range_values):
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
            for attribute_name, (comparison_operator, comparison_values) in filters.iteritems():
                comparison_func = get_comparison_func(comparison_operator)

                attribute = result.attrs.get(attribute_name)
                if attribute:
                    # Attribute found
                    attribute_value = attribute.values()[0]
                    if not comparison_func(attribute_value, *comparison_values):
                        passes_all_conditions = False
                        break
                elif comparison_operator == 'NULL':
                    # Comparison is NULL and we don't have the attribute
                    continue
                else:
                    # No attribute found and comparison is no NULL. This item fails
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

    def get_item(self, table_name, hash_key, range_key):
        table = self.tables.get(table_name)
        if not table:
            return None

        return table.get_item(hash_key, range_key)

    def query(self, table_name, hash_key, range_comparison, range_values):
        table = self.tables.get(table_name)
        if not table:
            return None, None

        return table.query(hash_key, range_comparison, range_values)

    def scan(self, table_name, filters):
        table = self.tables.get(table_name)
        if not table:
            return None, None, None

        return table.scan(filters)

    def delete_item(self, table_name, hash_key, range_key):
        table = self.tables.get(table_name)
        if not table:
            return None

        return table.delete_item(hash_key, range_key)


dynamodb_backend = DynamoDBBackend()
