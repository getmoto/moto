from collections import defaultdict
import datetime
import json

try:
        from collections import OrderedDict
except ImportError:
        # python 2.6 or earlier, use backport
        from ordereddict import OrderedDict


from moto.core import BaseBackend
from .comparisons import get_comparison_func
from .utils import unix_time


class DynamoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_json'):
            return obj.to_json()


def dynamo_json_dump(dynamo_object):
    return json.dumps(dynamo_object, cls=DynamoJsonEncoder)


class DynamoType(object):
    """
    http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DataModel.html#DataModelDataTypes
    """

    def __init__(self, type_as_dict):
        self.type = type_as_dict.keys()[0]
        self.value = type_as_dict.values()[0]

    def __hash__(self):
        return hash((self.type, self.value))

    def __eq__(self, other):
        return (
            self.type == other.type and
            self.value == other.value
        )

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value

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

class Item(object):
    def __init__(self, hash_key, hash_key_type, range_key, range_key_type, attrs):
        self.hash_key = hash_key
        self.hash_key_type = hash_key_type
        self.range_key = range_key
        self.range_key_type = range_key_type

        self.attrs = {}
        for key, value in attrs.iteritems():
            self.attrs[key] = DynamoType(value)

    def __repr__(self):
        return "Item: {0}".format(self.to_json())

    def to_json(self):
        attributes = {}
        for attribute_key, attribute in self.attrs.iteritems():
            attributes[attribute_key] = attribute.value

        return {
            "Attributes": attributes
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

    def __init__(self, table_name, schema=None, attr = None, throughput=None, indexes=None):
        self.name = table_name
        self.attr = attr
        self.schema = schema
        self.range_key_attr = None
        self.hash_key_attr = None
        self.range_key_type = None
        self.hash_key_type = None
        for elem in schema:
            if elem["KeyType"] == "HASH":
                self.hash_key_attr = elem["AttributeName"]
                self.hash_key_type = elem["KeyType"]
            else:
                self.range_key_attr = elem["AttributeName"]
                self.range_key_type = elem["KeyType"]
        if throughput is None:
             self.throughput = {u'WriteCapacityUnits': 10, u'ReadCapacityUnits': 10}
        else:
            self.throughput = throughput
        self.throughput["NumberOfDecreasesToday"] = 0
        self.indexes = indexes
        self.created_at = datetime.datetime.now()
        self.items = defaultdict(dict)
        
    @property
    def describe(self):
        results = {
        'Table': {
            'AttributeDefinitions': self.attr,
            'ProvisionedThroughput': self.throughput, 
            'TableSizeBytes': 0, 
            'TableName': self.name, 
            'TableStatus': 'ACTIVE', 
            'KeySchema': self.schema, 
            'ItemCount': len(self), 
            'CreationDateTime': unix_time(self.created_at)
            }
        }
        return results
    
    def __len__(self):
        count = 0
        for key, value in self.items.iteritems():
            if self.has_range_key:
                count += len(value)
            else:
                count += 1
        return count
    
    def put_item(self, item_attrs):
        hash_value = DynamoType(item_attrs.get(self.hash_key_attr))
        if self.has_range_key:
            range_value = DynamoType(item_attrs.get(self.range_key_attr))
        else:
            range_value = None

        item = Item(hash_value, self.hash_key_type, range_value, self.range_key_type, item_attrs)

        if range_value:
            self.items[hash_value][range_value] = item
        else:
            self.items[hash_value] = item
        return item
    
    def __nonzero__(self):
        return True
    
    @property
    def has_range_key(self):
        return self.range_key_attr is not None
    
    def get_item(self, hash_key, range_key):
        if self.has_range_key and not range_key:
            raise ValueError("Table has a range key, but no range key was passed into get_item")
        try:
            if range_key:
                return self.items[hash_key][range_key]
            else:
                return self.items[hash_key]
        except KeyError:
            return None
        
    def delete_item(self, hash_key, range_key):
        try:
            if range_key:
                return self.items[hash_key].pop(range_key)
            else:
                return self.items.pop(hash_key)
        except KeyError:
            return None
        
    def query(self, hash_key, range_comparison, range_objs):
        results = []
        last_page = True  # Once pagination is implemented, change this

        possible_results =  [ item for item in list(self.all_items()) if item.hash_key == hash_key] 
        if range_comparison:
            for result in possible_results:
                if result.range_key.compare(range_comparison, range_objs):
                    results.append(result)
        else:
            # If we're not filtering on range key, return all values
            results = possible_results

        results.sort(key=lambda item: item.range_key)
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
            for attribute_name, (comparison_operator, comparison_objs) in filters.iteritems():
                attribute = result.attrs.get(attribute_name)

                if attribute:
                    # Attribute found
                    if not attribute.compare(comparison_operator, comparison_objs):
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
    

class DynamoDBBackend(BaseBackend):

    def __init__(self):
        self.tables = OrderedDict()

    def create_table(self, name, **params):
        table = Table(name, **params)
        self.tables[name] = table
        return table

    def delete_table(self, name):
        return self.tables.pop(name, None)

    def update_table_throughput(self, name, throughput):
        table = self.tables[name]
        table.throughput = throughput
        return table

    def put_item(self, table_name, item_attrs):
        table = self.tables.get(table_name)
        if not table:
            return None
        return table.put_item(item_attrs)
    
    def get_table_keys_name(self, table_name):
        table = self.tables.get(table_name)
        if not table:
            return None, None
        else:
            return table.hash_key_attr, table.range_key_attr
         
    def get_keys_value(self, table, keys):
        if not table.hash_key_attr in keys or (table.has_range_key and not table.range_key_attr in keys):
            raise ValueError("Table has a range key, but no range key was passed into get_item")        
        hash_key = DynamoType(keys[table.hash_key_attr])    
        range_key = DynamoType(keys[table.range_key_attr]) if table.has_range_key else None
        return hash_key,range_key

    def get_item(self, table_name, keys):
        table = self.tables.get(table_name)
        if not table:
            return None
        hash_key,range_key = self.get_keys_value(table,keys)
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
        for key, (comparison_operator, comparison_values) in filters.iteritems():
            dynamo_types = [DynamoType(value) for value in comparison_values]
            scan_filters[key] = (comparison_operator, dynamo_types)

        return table.scan(scan_filters)
    
    def delete_item(self, table_name, keys):
        table = self.tables.get(table_name)
        if not table:
            return None
        hash_key, range_key = self.get_keys_value(table, keys)
        return table.delete_item(hash_key, range_key)


dynamodb_backend2 = DynamoDBBackend()
