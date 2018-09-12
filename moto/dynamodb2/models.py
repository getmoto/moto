from __future__ import unicode_literals
from collections import defaultdict
import copy
import datetime
import decimal
import json
import re

import boto3
from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from moto.core.utils import unix_time
from moto.core.exceptions import JsonRESTError
from .comparisons import get_comparison_func, get_filter_expression, Op


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
        self.type = list(type_as_dict)[0]
        self.value = list(type_as_dict.values())[0]

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

    @property
    def cast_value(self):
        if self.is_number():
            try:
                return int(self.value)
            except ValueError:
                return float(self.value)
        else:
            return self.value

    def to_json(self):
        return {self.type: self.value}

    def compare(self, range_comparison, range_objs):
        """
        Compares this type against comparison filters
        """
        range_values = [obj.cast_value for obj in range_objs]
        comparison_func = get_comparison_func(range_comparison)
        return comparison_func(self.cast_value, *range_values)

    def is_number(self):
        return self.type == 'N'

    def is_set(self):
        return self.type == 'SS' or self.type == 'NS' or self.type == 'BS'

    def same_type(self, other):
        return self.type == other.type


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
            attributes[attribute_key] = {
                attribute.type: attribute.value
            }

        return {
            "Attributes": attributes
        }

    def describe_attrs(self, attributes):
        if attributes:
            included = {}
            for key, value in self.attrs.items():
                if key in attributes:
                    included[key] = value
        else:
            included = self.attrs
        return {
            "Item": included
        }

    def update(self, update_expression, expression_attribute_names, expression_attribute_values):
        # Update subexpressions are identifiable by the operator keyword, so split on that and
        # get rid of the empty leading string.
        parts = [p for p in re.split(r'\b(SET|REMOVE|ADD|DELETE)\b', update_expression, flags=re.I) if p]
        # make sure that we correctly found only operator/value pairs
        assert len(parts) % 2 == 0, "Mismatched operators and values in update expression: '{}'".format(update_expression)
        for action, valstr in zip(parts[:-1:2], parts[1::2]):
            action = action.upper()

            # "Should" retain arguments in side (...)
            values = re.split(r',(?![^(]*\))', valstr)
            for value in values:
                # A Real value
                value = value.lstrip(":").rstrip(",").strip()
                for k, v in expression_attribute_names.items():
                    value = re.sub(r'{0}\b'.format(k), v, value)

                if action == "REMOVE":
                    self.attrs.pop(value, None)
                elif action == 'SET':
                    key, value = value.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # If not exists, changes value to a default if needed, else its the same as it was
                    if value.startswith('if_not_exists'):
                        # Function signature
                        match = re.match(r'.*if_not_exists\((?P<path>.+),\s*(?P<default>.+)\).*', value)
                        if not match:
                            raise TypeError

                        path, value = match.groups()

                        # If it already exists, get its value so we dont overwrite it
                        if path in self.attrs:
                            value = self.attrs[path].cast_value

                    if value in expression_attribute_values:
                        value = DynamoType(expression_attribute_values[value])
                    else:
                        value = DynamoType({"S": value})

                    if '.' not in key:
                        self.attrs[key] = value
                    else:
                        # Handle nested dict updates
                        key_parts = key.split('.')
                        attr = key_parts.pop(0)
                        if attr not in self.attrs:
                            raise ValueError

                        last_val = self.attrs[attr].value
                        for key_part in key_parts:
                            # Hack but it'll do, traverses into a dict
                            last_val_type = list(last_val.keys())
                            if last_val_type and last_val_type[0] == 'M':
                                    last_val = last_val['M']

                            if key_part not in last_val:
                                last_val[key_part] = {'M': {}}

                            last_val = last_val[key_part]

                        # We have reference to a nested object but we cant just assign to it
                        current_type = list(last_val.keys())[0]
                        if current_type == value.type:
                            last_val[current_type] = value.value
                        else:
                            last_val[value.type] = value.value
                            del last_val[current_type]

                elif action == 'ADD':
                    key, value = value.split(" ", 1)
                    key = key.strip()
                    value_str = value.strip()
                    if value_str in expression_attribute_values:
                        dyn_value = DynamoType(expression_attribute_values[value])
                    else:
                        raise TypeError

                    # Handle adding numbers - value gets added to existing value,
                    # or added to 0 if it doesn't exist yet
                    if dyn_value.is_number():
                        existing = self.attrs.get(key, DynamoType({"N": '0'}))
                        if not existing.same_type(dyn_value):
                            raise TypeError()
                        self.attrs[key] = DynamoType({"N": str(
                            decimal.Decimal(existing.value) +
                            decimal.Decimal(dyn_value.value)
                        )})

                    # Handle adding sets - value is added to the set, or set is
                    # created with only this value if it doesn't exist yet
                    # New value must be of same set type as previous value
                    elif dyn_value.is_set():
                        existing = self.attrs.get(key, DynamoType({dyn_value.type: {}}))
                        if not existing.same_type(dyn_value):
                            raise TypeError()
                        new_set = set(existing.value).union(dyn_value.value)
                        self.attrs[key] = DynamoType({existing.type: list(new_set)})
                    else:  # Number and Sets are the only supported types for ADD
                        raise TypeError

                elif action == 'DELETE':
                    key, value = value.split(" ", 1)
                    key = key.strip()
                    value_str = value.strip()
                    if value_str in expression_attribute_values:
                        dyn_value = DynamoType(expression_attribute_values[value])
                    else:
                        raise TypeError

                    if not dyn_value.is_set():
                        raise TypeError
                    existing = self.attrs.get(key, None)
                    if existing:
                        if not existing.same_type(dyn_value):
                            raise TypeError
                        new_set = set(existing.value).difference(dyn_value.value)
                        self.attrs[key] = DynamoType({existing.type: list(new_set)})
                else:
                    raise NotImplementedError('{} update action not yet supported'.format(action))

    def update_with_attribute_updates(self, attribute_updates):
        for attribute_name, update_action in attribute_updates.items():
            action = update_action['Action']
            if action == 'DELETE' and 'Value' not in update_action:
                if attribute_name in self.attrs:
                    del self.attrs[attribute_name]
                continue
            new_value = list(update_action['Value'].values())[0]
            if action == 'PUT':
                # TODO deal with other types
                if isinstance(new_value, list) or isinstance(new_value, set):
                    self.attrs[attribute_name] = DynamoType({"SS": new_value})
                elif isinstance(new_value, dict):
                    self.attrs[attribute_name] = DynamoType({"M": new_value})
                elif update_action['Value'].keys() == ['N']:
                    self.attrs[attribute_name] = DynamoType({"N": new_value})
                elif update_action['Value'].keys() == ['NULL']:
                    if attribute_name in self.attrs:
                        del self.attrs[attribute_name]
                else:
                    self.attrs[attribute_name] = DynamoType({"S": new_value})
            elif action == 'ADD':
                if set(update_action['Value'].keys()) == set(['N']):
                    existing = self.attrs.get(
                        attribute_name, DynamoType({"N": '0'}))
                    self.attrs[attribute_name] = DynamoType({"N": str(
                        decimal.Decimal(existing.value) +
                        decimal.Decimal(new_value)
                    )})
                elif set(update_action['Value'].keys()) == set(['SS']):
                    existing = self.attrs.get(attribute_name, DynamoType({"SS": {}}))
                    new_set = set(existing.value).union(set(new_value))
                    self.attrs[attribute_name] = DynamoType({
                        "SS": list(new_set)
                    })
                else:
                    # TODO: implement other data types
                    raise NotImplementedError(
                        'ADD not supported for %s' % ', '.join(update_action['Value'].keys()))


class Table(BaseModel):

    def __init__(self, table_name, schema=None, attr=None, throughput=None, indexes=None, global_indexes=None):
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
            self.throughput = {
                'WriteCapacityUnits': 10, 'ReadCapacityUnits': 10}
        else:
            self.throughput = throughput
        self.throughput["NumberOfDecreasesToday"] = 0
        self.indexes = indexes
        self.global_indexes = global_indexes if global_indexes else []
        self.created_at = datetime.datetime.utcnow()
        self.items = defaultdict(dict)
        self.table_arn = self._generate_arn(table_name)
        self.tags = []
        self.ttl = {
            'TimeToLiveStatus': 'DISABLED'  # One of 'ENABLING'|'DISABLING'|'ENABLED'|'DISABLED',
            # 'AttributeName': 'string'  # Can contain this
        }

    def _generate_arn(self, name):
        return 'arn:aws:dynamodb:us-east-1:123456789011:table/' + name

    def describe(self, base_key='TableDescription'):
        results = {
            base_key: {
                'AttributeDefinitions': self.attr,
                'ProvisionedThroughput': self.throughput,
                'TableSizeBytes': 0,
                'TableName': self.name,
                'TableStatus': 'ACTIVE',
                'TableArn': self.table_arn,
                'KeySchema': self.schema,
                'ItemCount': len(self),
                'CreationDateTime': unix_time(self.created_at),
                'GlobalSecondaryIndexes': [index for index in self.global_indexes],
                'LocalSecondaryIndexes': [index for index in self.indexes],
            }
        }
        return results

    def __len__(self):
        count = 0
        for key, value in self.items.items():
            if self.has_range_key:
                count += len(value)
            else:
                count += 1
        return count

    @property
    def hash_key_names(self):
        keys = [self.hash_key_attr]
        for index in self.global_indexes:
            hash_key = None
            for key in index['KeySchema']:
                if key['KeyType'] == 'HASH':
                    hash_key = key['AttributeName']
            keys.append(hash_key)
        return keys

    @property
    def range_key_names(self):
        keys = [self.range_key_attr]
        for index in self.global_indexes:
            range_key = None
            for key in index['KeySchema']:
                if key['KeyType'] == 'RANGE':
                    range_key = keys.append(key['AttributeName'])
            keys.append(range_key)
        return keys

    def put_item(self, item_attrs, expected=None, overwrite=False):
        hash_value = DynamoType(item_attrs.get(self.hash_key_attr))
        if self.has_range_key:
            range_value = DynamoType(item_attrs.get(self.range_key_attr))
        else:
            range_value = None

        item = Item(hash_value, self.hash_key_type, range_value,
                    self.range_key_type, item_attrs)

        if not overwrite:
            if expected is None:
                expected = {}
                lookup_range_value = range_value
            else:
                expected_range_value = expected.get(
                    self.range_key_attr, {}).get("Value")
                if(expected_range_value is None):
                    lookup_range_value = range_value
                else:
                    lookup_range_value = DynamoType(expected_range_value)

            current = self.get_item(hash_value, lookup_range_value)

            if current is None:
                current_attr = {}
            elif hasattr(current, 'attrs'):
                current_attr = current.attrs
            else:
                current_attr = current

            for key, val in expected.items():
                if 'Exists' in val and val['Exists'] is False \
                        or 'ComparisonOperator' in val and val['ComparisonOperator'] == 'NULL':
                    if key in current_attr:
                        raise ValueError("The conditional request failed")
                elif key not in current_attr:
                    raise ValueError("The conditional request failed")
                elif 'Value' in val and DynamoType(val['Value']).value != current_attr[key].value:
                    raise ValueError("The conditional request failed")
                elif 'ComparisonOperator' in val:
                    comparison_func = get_comparison_func(
                        val['ComparisonOperator'])
                    dynamo_types = [
                        DynamoType(ele) for ele in
                        val.get("AttributeValueList", [])
                    ]
                    for t in dynamo_types:
                        if not comparison_func(current_attr[key].value, t.value):
                            raise ValueError('The conditional request failed')
        if range_value:
            self.items[hash_value][range_value] = item
        else:
            self.items[hash_value] = item
        return item

    def __nonzero__(self):
        return True

    def __bool__(self):
        return self.__nonzero__()

    @property
    def has_range_key(self):
        return self.range_key_attr is not None

    def get_item(self, hash_key, range_key=None):
        if self.has_range_key and not range_key:
            raise ValueError(
                "Table has a range key, but no range key was passed into get_item")
        try:
            if range_key:
                return self.items[hash_key][range_key]

            if hash_key in self.items:
                return self.items[hash_key]

            raise KeyError
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

    def query(self, hash_key, range_comparison, range_objs, limit,
              exclusive_start_key, scan_index_forward, projection_expression,
              index_name=None, filter_expression=None, **filter_kwargs):
        results = []
        if index_name:
            all_indexes = (self.global_indexes or []) + (self.indexes or [])
            indexes_by_name = dict((i['IndexName'], i) for i in all_indexes)
            if index_name not in indexes_by_name:
                raise ValueError('Invalid index: %s for table: %s. Available indexes are: %s' % (
                    index_name, self.name, ', '.join(indexes_by_name.keys())
                ))

            index = indexes_by_name[index_name]
            try:
                index_hash_key = [key for key in index[
                    'KeySchema'] if key['KeyType'] == 'HASH'][0]
            except IndexError:
                raise ValueError('Missing Hash Key. KeySchema: %s' %
                                 index['KeySchema'])

            possible_results = []
            for item in self.all_items():
                if not isinstance(item, Item):
                    continue
                item_hash_key = item.attrs.get(index_hash_key['AttributeName'])
                if item_hash_key and item_hash_key == hash_key:
                    possible_results.append(item)
        else:
            possible_results = [item for item in list(self.all_items()) if isinstance(
                item, Item) and item.hash_key == hash_key]

        if index_name:
            try:
                index_range_key = [key for key in index[
                    'KeySchema'] if key['KeyType'] == 'RANGE'][0]
            except IndexError:
                index_range_key = None

        if range_comparison:
            if index_name and not index_range_key:
                raise ValueError(
                    'Range Key comparison but no range key found for index: %s' % index_name)

            elif index_name:
                for result in possible_results:
                    if result.attrs.get(index_range_key['AttributeName']).compare(range_comparison, range_objs):
                        results.append(result)
            else:
                for result in possible_results:
                    if result.range_key.compare(range_comparison, range_objs):
                        results.append(result)

        if filter_kwargs:
            for result in possible_results:
                for field, value in filter_kwargs.items():
                    dynamo_types = [DynamoType(ele) for ele in value[
                        "AttributeValueList"]]
                    if result.attrs.get(field).compare(value['ComparisonOperator'], dynamo_types):
                        results.append(result)

        if not range_comparison and not filter_kwargs:
            # If we're not filtering on range key or on an index return all
            # values
            results = possible_results

        if index_name:

            if index_range_key:
                results.sort(key=lambda item: item.attrs[index_range_key['AttributeName']].value
                             if item.attrs.get(index_range_key['AttributeName']) else None)
        else:
            results.sort(key=lambda item: item.range_key)

        if scan_index_forward is False:
            results.reverse()

        scanned_count = len(list(self.all_items()))

        if filter_expression is not None:
            results = [item for item in results if filter_expression.expr(item)]

        if projection_expression:
            expressions = [x.strip() for x in projection_expression.split(',')]
            results = copy.deepcopy(results)
            for result in results:
                for attr in list(result.attrs):
                    if attr not in expressions:
                        result.attrs.pop(attr)

        results, last_evaluated_key = self._trim_results(results, limit,
                                                         exclusive_start_key)
        return results, scanned_count, last_evaluated_key

    def all_items(self):
        for hash_set in self.items.values():
            if self.range_key_attr:
                for item in hash_set.values():
                    yield item
            else:
                yield hash_set

    def scan(self, filters, limit, exclusive_start_key, filter_expression=None):
        results = []
        scanned_count = 0

        for item in self.all_items():
            scanned_count += 1
            passes_all_conditions = True
            for attribute_name, (comparison_operator, comparison_objs) in filters.items():
                attribute = item.attrs.get(attribute_name)

                if attribute:
                    # Attribute found
                    if not attribute.compare(comparison_operator, comparison_objs):
                        passes_all_conditions = False
                        break
                elif comparison_operator == 'NULL':
                    # Comparison is NULL and we don't have the attribute
                    continue
                else:
                    # No attribute found and comparison is no NULL. This item
                    # fails
                    passes_all_conditions = False
                    break

            if filter_expression is not None:
                passes_all_conditions &= filter_expression.expr(item)

            if passes_all_conditions:
                results.append(item)

        results, last_evaluated_key = self._trim_results(results, limit,
                                                         exclusive_start_key)
        return results, scanned_count, last_evaluated_key

    def _trim_results(self, results, limit, exclusive_start_key):
        if exclusive_start_key is not None:
            hash_key = DynamoType(exclusive_start_key.get(self.hash_key_attr))
            range_key = exclusive_start_key.get(self.range_key_attr)
            if range_key is not None:
                range_key = DynamoType(range_key)
            for i in range(len(results)):
                if results[i].hash_key == hash_key and results[i].range_key == range_key:
                    results = results[i + 1:]
                    break

        last_evaluated_key = None
        if limit and len(results) > limit:
            results = results[:limit]
            last_evaluated_key = {
                self.hash_key_attr: results[-1].hash_key
            }
            if results[-1].range_key is not None:
                last_evaluated_key[self.range_key_attr] = results[-1].range_key

        return results, last_evaluated_key

    def lookup(self, *args, **kwargs):
        if not self.schema:
            self.describe()
        for x, arg in enumerate(args):
            kwargs[self.schema[x].name] = arg
        ret = self.get_item(**kwargs)
        if not ret.keys():
            return None
        return ret


class DynamoDBBackend(BaseBackend):

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.tables = OrderedDict()

    def reset(self):
        region_name = self.region_name

        self.__dict__ = {}
        self.__init__(region_name)

    def create_table(self, name, **params):
        if name in self.tables:
            return None
        table = Table(name, **params)
        self.tables[name] = table
        return table

    def delete_table(self, name):
        return self.tables.pop(name, None)

    def tag_resource(self, table_arn, tags):
        for table in self.tables:
            if self.tables[table].table_arn == table_arn:
                self.tables[table].tags.extend(tags)

    def untag_resource(self, table_arn, tag_keys):
        for table in self.tables:
            if self.tables[table].table_arn == table_arn:
                self.tables[table].tags = [tag for tag in self.tables[table].tags if tag['Key'] not in tag_keys]

    def list_tags_of_resource(self, table_arn):
        required_table = None
        for table in self.tables:
            if self.tables[table].table_arn == table_arn:
                required_table = self.tables[table]
        return required_table.tags

    def update_table_throughput(self, name, throughput):
        table = self.tables[name]
        table.throughput = throughput
        return table

    def update_table_global_indexes(self, name, global_index_updates):
        table = self.tables[name]
        gsis_by_name = dict((i['IndexName'], i) for i in table.global_indexes)
        for gsi_update in global_index_updates:
            gsi_to_create = gsi_update.get('Create')
            gsi_to_update = gsi_update.get('Update')
            gsi_to_delete = gsi_update.get('Delete')

            if gsi_to_delete:
                index_name = gsi_to_delete['IndexName']
                if index_name not in gsis_by_name:
                    raise ValueError('Global Secondary Index does not exist, but tried to delete: %s' %
                                     gsi_to_delete['IndexName'])

                del gsis_by_name[index_name]

            if gsi_to_update:
                index_name = gsi_to_update['IndexName']
                if index_name not in gsis_by_name:
                    raise ValueError('Global Secondary Index does not exist, but tried to update: %s' %
                                     gsi_to_update['IndexName'])
                gsis_by_name[index_name].update(gsi_to_update)

            if gsi_to_create:
                if gsi_to_create['IndexName'] in gsis_by_name:
                    raise ValueError(
                        'Global Secondary Index already exists: %s' % gsi_to_create['IndexName'])

                gsis_by_name[gsi_to_create['IndexName']] = gsi_to_create

        # in python 3.6, dict.values() returns a dict_values object, but we expect it to be a list in other
        # parts of the codebase
        table.global_indexes = list(gsis_by_name.values())
        return table

    def put_item(self, table_name, item_attrs, expected=None, overwrite=False):
        table = self.tables.get(table_name)
        if not table:
            return None
        return table.put_item(item_attrs, expected, overwrite)

    def get_table_keys_name(self, table_name, keys):
        """
        Given a set of keys, extracts the key and range key
        """
        table = self.tables.get(table_name)
        if not table:
            return None, None
        else:
            if len(keys) == 1:
                for key in keys:
                    if key in table.hash_key_names:
                        return key, None
            # for potential_hash, potential_range in zip(table.hash_key_names, table.range_key_names):
            #     if set([potential_hash, potential_range]) == set(keys):
            #         return potential_hash, potential_range
            potential_hash, potential_range = None, None
            for key in set(keys):
                if key in table.hash_key_names:
                    potential_hash = key
                elif key in table.range_key_names:
                    potential_range = key
            return potential_hash, potential_range

    def get_keys_value(self, table, keys):
        if table.hash_key_attr not in keys or (table.has_range_key and table.range_key_attr not in keys):
            raise ValueError(
                "Table has a range key, but no range key was passed into get_item")
        hash_key = DynamoType(keys[table.hash_key_attr])
        range_key = DynamoType(
            keys[table.range_key_attr]) if table.has_range_key else None
        return hash_key, range_key

    def get_table(self, table_name):
        return self.tables.get(table_name)

    def get_item(self, table_name, keys):
        table = self.get_table(table_name)
        if not table:
            raise ValueError("No table found")
        hash_key, range_key = self.get_keys_value(table, keys)
        return table.get_item(hash_key, range_key)

    def query(self, table_name, hash_key_dict, range_comparison, range_value_dicts,
              limit, exclusive_start_key, scan_index_forward, projection_expression, index_name=None,
              expr_names=None, expr_values=None, filter_expression=None,
              **filter_kwargs):
        table = self.tables.get(table_name)
        if not table:
            return None, None

        hash_key = DynamoType(hash_key_dict)
        range_values = [DynamoType(range_value)
                        for range_value in range_value_dicts]

        if filter_expression is not None:
            filter_expression = get_filter_expression(filter_expression, expr_names, expr_values)
        else:
            filter_expression = Op(None, None)  # Will always eval to true

        return table.query(hash_key, range_comparison, range_values, limit,
                           exclusive_start_key, scan_index_forward, projection_expression, index_name, filter_expression, **filter_kwargs)

    def scan(self, table_name, filters, limit, exclusive_start_key, filter_expression, expr_names, expr_values):
        table = self.tables.get(table_name)
        if not table:
            return None, None, None

        scan_filters = {}
        for key, (comparison_operator, comparison_values) in filters.items():
            dynamo_types = [DynamoType(value) for value in comparison_values]
            scan_filters[key] = (comparison_operator, dynamo_types)

        if filter_expression is not None:
            filter_expression = get_filter_expression(filter_expression, expr_names, expr_values)
        else:
            filter_expression = Op(None, None)  # Will always eval to true

        return table.scan(scan_filters, limit, exclusive_start_key, filter_expression)

    def update_item(self, table_name, key, update_expression, attribute_updates, expression_attribute_names,
                    expression_attribute_values, expected=None):
        table = self.get_table(table_name)

        if all([table.hash_key_attr in key, table.range_key_attr in key]):
            # Covers cases where table has hash and range keys, ``key`` param
            # will be a dict
            hash_value = DynamoType(key[table.hash_key_attr])
            range_value = DynamoType(key[table.range_key_attr])
        elif table.hash_key_attr in key:
            # Covers tables that have a range key where ``key`` param is a dict
            hash_value = DynamoType(key[table.hash_key_attr])
            range_value = None
        else:
            # Covers other cases
            hash_value = DynamoType(key)
            range_value = None

        item = table.get_item(hash_value, range_value)

        if item is None:
            item_attr = {}
        elif hasattr(item, 'attrs'):
            item_attr = item.attrs
        else:
            item_attr = item

        if not expected:
            expected = {}

        for key, val in expected.items():
            if 'Exists' in val and val['Exists'] is False \
                    or 'ComparisonOperator' in val and val['ComparisonOperator'] == 'NULL':
                if key in item_attr:
                    raise ValueError("The conditional request failed")
            elif key not in item_attr:
                raise ValueError("The conditional request failed")
            elif 'Value' in val and DynamoType(val['Value']).value != item_attr[key].value:
                raise ValueError("The conditional request failed")
            elif 'ComparisonOperator' in val:
                comparison_func = get_comparison_func(
                    val['ComparisonOperator'])
                dynamo_types = [
                    DynamoType(ele) for ele in
                    val.get("AttributeValueList", [])
                ]
                for t in dynamo_types:
                    if not comparison_func(item_attr[key].value, t.value):
                        raise ValueError('The conditional request failed')

        # Update does not fail on new items, so create one
        if item is None:
            data = {
                table.hash_key_attr: {
                    hash_value.type: hash_value.value,
                },
            }
            if range_value:
                data.update({
                    table.range_key_attr: {
                        range_value.type: range_value.value,
                    }
                })

            table.put_item(data)
            item = table.get_item(hash_value, range_value)

        if update_expression:
            item.update(update_expression, expression_attribute_names,
                        expression_attribute_values)
        else:
            item.update_with_attribute_updates(attribute_updates)
        return item

    def delete_item(self, table_name, keys):
        table = self.get_table(table_name)
        if not table:
            return None
        hash_key, range_key = self.get_keys_value(table, keys)
        return table.delete_item(hash_key, range_key)

    def update_ttl(self, table_name, ttl_spec):
        table = self.tables.get(table_name)
        if table is None:
            raise JsonRESTError('ResourceNotFound', 'Table not found')

        if 'Enabled' not in ttl_spec or 'AttributeName' not in ttl_spec:
            raise JsonRESTError('InvalidParameterValue',
                                'TimeToLiveSpecification does not contain Enabled and AttributeName')

        if ttl_spec['Enabled']:
            table.ttl['TimeToLiveStatus'] = 'ENABLED'
        else:
            table.ttl['TimeToLiveStatus'] = 'DISABLED'
        table.ttl['AttributeName'] = ttl_spec['AttributeName']

    def describe_ttl(self, table_name):
        table = self.tables.get(table_name)
        if table is None:
            raise JsonRESTError('ResourceNotFound', 'Table not found')

        return table.ttl


available_regions = boto3.session.Session().get_available_regions("dynamodb")
dynamodb_backends = {region: DynamoDBBackend(region_name=region) for region in available_regions}
