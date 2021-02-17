from __future__ import unicode_literals
from collections import defaultdict
import copy
import datetime
import decimal
import json
import re
import uuid

from boto3 import Session
from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel, CloudFormationModel
from moto.core.utils import unix_time
from moto.core.exceptions import JsonRESTError
from moto.dynamodb2.comparisons import get_filter_expression
from moto.dynamodb2.comparisons import get_expected
from moto.dynamodb2.exceptions import (
    InvalidIndexNameError,
    ItemSizeTooLarge,
    ItemSizeToUpdateTooLarge,
    ConditionalCheckFailed,
    TransactionCanceledException,
    EmptyKeyAttributeException,
)
from moto.dynamodb2.models.utilities import bytesize
from moto.dynamodb2.models.dynamo_type import DynamoType
from moto.dynamodb2.parsing.executors import UpdateExpressionExecutor
from moto.dynamodb2.parsing.expressions import UpdateExpressionParser
from moto.dynamodb2.parsing.validators import UpdateExpressionValidator


class DynamoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_json"):
            return obj.to_json()


def dynamo_json_dump(dynamo_object):
    return json.dumps(dynamo_object, cls=DynamoJsonEncoder)


# https://github.com/spulec/moto/issues/1874
# Ensure that the total size of an item does not exceed 400kb
class LimitedSizeDict(dict):
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        current_item_size = sum(
            [
                item.size() if type(item) == DynamoType else bytesize(str(item))
                for item in (list(self.keys()) + list(self.values()))
            ]
        )
        new_item_size = bytesize(key) + (
            value.size() if type(value) == DynamoType else bytesize(str(value))
        )
        # Official limit is set to 400000 (400KB)
        # Manual testing confirms that the actual limit is between 409 and 410KB
        # We'll set the limit to something in between to be safe
        if (current_item_size + new_item_size) > 405000:
            raise ItemSizeTooLarge
        super(LimitedSizeDict, self).__setitem__(key, value)


class Item(BaseModel):
    def __init__(self, hash_key, hash_key_type, range_key, range_key_type, attrs):
        self.hash_key = hash_key
        self.hash_key_type = hash_key_type
        self.range_key = range_key
        self.range_key_type = range_key_type

        self.attrs = LimitedSizeDict()
        for key, value in attrs.items():
            self.attrs[key] = DynamoType(value)

    def __eq__(self, other):
        return all(
            [
                self.hash_key == other.hash_key,
                self.hash_key_type == other.hash_key_type,
                self.range_key == other.range_key,
                self.range_key_type == other.range_key_type,
                self.attrs == other.attrs,
            ]
        )

    def __repr__(self):
        return "Item: {0}".format(self.to_json())

    def size(self):
        return sum(bytesize(key) + value.size() for key, value in self.attrs.items())

    def to_json(self):
        attributes = {}
        for attribute_key, attribute in self.attrs.items():
            attributes[attribute_key] = {attribute.type: attribute.value}

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

    def validate_no_empty_key_values(self, attribute_updates, key_attributes):
        for attribute_name, update_action in attribute_updates.items():
            action = update_action.get("Action") or "PUT"  # PUT is default
            new_value = next(iter(update_action["Value"].values()))
            if action == "PUT" and new_value == "" and attribute_name in key_attributes:
                raise EmptyKeyAttributeException

    def update_with_attribute_updates(self, attribute_updates):
        for attribute_name, update_action in attribute_updates.items():
            # Use default Action value, if no explicit Action is passed.
            # Default value is 'Put', according to
            # Boto3 DynamoDB.Client.update_item documentation.
            action = update_action.get("Action", "PUT")
            if action == "DELETE" and "Value" not in update_action:
                if attribute_name in self.attrs:
                    del self.attrs[attribute_name]
                continue
            new_value = list(update_action["Value"].values())[0]
            if action == "PUT":
                # TODO deal with other types
                if set(update_action["Value"].keys()) == set(["SS"]):
                    self.attrs[attribute_name] = DynamoType({"SS": new_value})
                elif isinstance(new_value, list):
                    self.attrs[attribute_name] = DynamoType({"L": new_value})
                elif isinstance(new_value, dict):
                    self.attrs[attribute_name] = DynamoType({"M": new_value})
                elif set(update_action["Value"].keys()) == set(["N"]):
                    self.attrs[attribute_name] = DynamoType({"N": new_value})
                elif set(update_action["Value"].keys()) == set(["NULL"]):
                    if attribute_name in self.attrs:
                        del self.attrs[attribute_name]
                else:
                    self.attrs[attribute_name] = DynamoType({"S": new_value})
            elif action == "ADD":
                if set(update_action["Value"].keys()) == set(["N"]):
                    existing = self.attrs.get(attribute_name, DynamoType({"N": "0"}))
                    self.attrs[attribute_name] = DynamoType(
                        {
                            "N": str(
                                decimal.Decimal(existing.value)
                                + decimal.Decimal(new_value)
                            )
                        }
                    )
                elif set(update_action["Value"].keys()) == set(["SS"]):
                    existing = self.attrs.get(attribute_name, DynamoType({"SS": {}}))
                    new_set = set(existing.value).union(set(new_value))
                    self.attrs[attribute_name] = DynamoType({"SS": list(new_set)})
                elif set(update_action["Value"].keys()) == {"L"}:
                    existing = self.attrs.get(attribute_name, DynamoType({"L": []}))
                    new_list = existing.value + new_value
                    self.attrs[attribute_name] = DynamoType({"L": new_list})
                else:
                    # TODO: implement other data types
                    raise NotImplementedError(
                        "ADD not supported for %s"
                        % ", ".join(update_action["Value"].keys())
                    )
            elif action == "DELETE":
                if set(update_action["Value"].keys()) == set(["SS"]):
                    existing = self.attrs.get(attribute_name, DynamoType({"SS": {}}))
                    new_set = set(existing.value).difference(set(new_value))
                    self.attrs[attribute_name] = DynamoType({"SS": list(new_set)})
                else:
                    raise NotImplementedError(
                        "ADD not supported for %s"
                        % ", ".join(update_action["Value"].keys())
                    )
            else:
                raise NotImplementedError(
                    "%s action not support for update_with_attribute_updates" % action
                )

    # Filter using projection_expression
    # Ensure a deep copy is used to filter, otherwise actual data will be removed
    def filter(self, projection_expression):
        expressions = [x.strip() for x in projection_expression.split(",")]
        top_level_expressions = [
            expr[0 : expr.index(".")] for expr in expressions if "." in expr
        ]
        for attr in list(self.attrs):
            if attr not in expressions and attr not in top_level_expressions:
                self.attrs.pop(attr)
            if attr in top_level_expressions:
                relevant_expressions = [
                    expr[len(attr + ".") :]
                    for expr in expressions
                    if expr.startswith(attr + ".")
                ]
                self.attrs[attr].filter(relevant_expressions)


class StreamRecord(BaseModel):
    def __init__(self, table, stream_type, event_name, old, new, seq):
        old_a = old.to_json()["Attributes"] if old is not None else {}
        new_a = new.to_json()["Attributes"] if new is not None else {}

        rec = old if old is not None else new
        keys = {table.hash_key_attr: rec.hash_key.to_json()}
        if table.range_key_attr is not None:
            keys[table.range_key_attr] = rec.range_key.to_json()

        self.record = {
            "eventID": uuid.uuid4().hex,
            "eventName": event_name,
            "eventSource": "aws:dynamodb",
            "eventVersion": "1.0",
            "awsRegion": "us-east-1",
            "dynamodb": {
                "StreamViewType": stream_type,
                "ApproximateCreationDateTime": datetime.datetime.utcnow().isoformat(),
                "SequenceNumber": str(seq),
                "SizeBytes": 1,
                "Keys": keys,
            },
        }

        if stream_type in ("NEW_IMAGE", "NEW_AND_OLD_IMAGES"):
            self.record["dynamodb"]["NewImage"] = new_a
        if stream_type in ("OLD_IMAGE", "NEW_AND_OLD_IMAGES"):
            self.record["dynamodb"]["OldImage"] = old_a

        # This is a substantial overestimate but it's the easiest to do now
        self.record["dynamodb"]["SizeBytes"] = len(
            dynamo_json_dump(self.record["dynamodb"])
        )

    def to_json(self):
        return self.record


class StreamShard(BaseModel):
    def __init__(self, table):
        self.table = table
        self.id = "shardId-00000001541626099285-f35f62ef"
        self.starting_sequence_number = 1100000000017454423009
        self.items = []
        self.created_on = datetime.datetime.utcnow()

    def to_json(self):
        return {
            "ShardId": self.id,
            "SequenceNumberRange": {
                "StartingSequenceNumber": str(self.starting_sequence_number)
            },
        }

    def add(self, old, new):
        t = self.table.stream_specification["StreamViewType"]
        if old is None:
            event_name = "INSERT"
        elif new is None:
            event_name = "REMOVE"
        else:
            event_name = "MODIFY"
        seq = len(self.items) + self.starting_sequence_number
        self.items.append(StreamRecord(self.table, t, event_name, old, new, seq))
        result = None
        from moto.awslambda import lambda_backends

        for arn, esm in self.table.lambda_event_source_mappings.items():
            region = arn[
                len("arn:aws:lambda:") : arn.index(":", len("arn:aws:lambda:"))
            ]

            result = lambda_backends[region].send_dynamodb_items(
                arn, self.items, esm.event_source_arn
            )

        if result:
            self.items = []

    def get(self, start, quantity):
        start -= self.starting_sequence_number
        assert start >= 0
        end = start + quantity
        return [i.to_json() for i in self.items[start:end]]


class SecondaryIndex(BaseModel):
    def project(self, item):
        """
        Enforces the ProjectionType of this Index (LSI/GSI)
        Removes any non-wanted attributes from the item
        :param item:
        :return:
        """
        if self.projection:
            projection_type = self.projection.get("ProjectionType", None)
            key_attributes = self.table_key_attrs + [
                key["AttributeName"] for key in self.schema
            ]

            if projection_type == "KEYS_ONLY":
                item.filter(",".join(key_attributes))
            elif projection_type == "INCLUDE":
                allowed_attributes = key_attributes + self.projection.get(
                    "NonKeyAttributes", []
                )
                item.filter(",".join(allowed_attributes))
            # ALL is handled implicitly by not filtering
        return item


class LocalSecondaryIndex(SecondaryIndex):
    def __init__(self, index_name, schema, projection, table_key_attrs):
        self.name = index_name
        self.schema = schema
        self.projection = projection
        self.table_key_attrs = table_key_attrs

    def describe(self):
        return {
            "IndexName": self.name,
            "KeySchema": self.schema,
            "Projection": self.projection,
        }

    @staticmethod
    def create(dct, table_key_attrs):
        return LocalSecondaryIndex(
            index_name=dct["IndexName"],
            schema=dct["KeySchema"],
            projection=dct["Projection"],
            table_key_attrs=table_key_attrs,
        )


class GlobalSecondaryIndex(SecondaryIndex):
    def __init__(
        self,
        index_name,
        schema,
        projection,
        table_key_attrs,
        status="ACTIVE",
        throughput=None,
    ):
        self.name = index_name
        self.schema = schema
        self.projection = projection
        self.table_key_attrs = table_key_attrs
        self.status = status
        self.throughput = throughput or {
            "ReadCapacityUnits": 0,
            "WriteCapacityUnits": 0,
        }

    def describe(self):
        return {
            "IndexName": self.name,
            "KeySchema": self.schema,
            "Projection": self.projection,
            "IndexStatus": self.status,
            "ProvisionedThroughput": self.throughput,
        }

    @staticmethod
    def create(dct, table_key_attrs):
        return GlobalSecondaryIndex(
            index_name=dct["IndexName"],
            schema=dct["KeySchema"],
            projection=dct["Projection"],
            table_key_attrs=table_key_attrs,
            throughput=dct.get("ProvisionedThroughput", None),
        )

    def update(self, u):
        self.name = u.get("IndexName", self.name)
        self.schema = u.get("KeySchema", self.schema)
        self.projection = u.get("Projection", self.projection)
        self.throughput = u.get("ProvisionedThroughput", self.throughput)


class Table(CloudFormationModel):
    def __init__(
        self,
        table_name,
        schema=None,
        attr=None,
        throughput=None,
        indexes=None,
        global_indexes=None,
        streams=None,
    ):
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
        self.table_key_attrs = [
            key for key in (self.hash_key_attr, self.range_key_attr) if key
        ]
        if throughput is None:
            self.throughput = {"WriteCapacityUnits": 10, "ReadCapacityUnits": 10}
        else:
            self.throughput = throughput
        self.throughput["NumberOfDecreasesToday"] = 0
        self.indexes = [
            LocalSecondaryIndex.create(i, self.table_key_attrs)
            for i in (indexes if indexes else [])
        ]
        self.global_indexes = [
            GlobalSecondaryIndex.create(i, self.table_key_attrs)
            for i in (global_indexes if global_indexes else [])
        ]
        self.created_at = datetime.datetime.utcnow()
        self.items = defaultdict(dict)
        self.table_arn = self._generate_arn(table_name)
        self.tags = []
        self.ttl = {
            "TimeToLiveStatus": "DISABLED"  # One of 'ENABLING'|'DISABLING'|'ENABLED'|'DISABLED',
            # 'AttributeName': 'string'  # Can contain this
        }
        self.set_stream_specification(streams)
        self.lambda_event_source_mappings = {}
        self.continuous_backups = {
            "ContinuousBackupsStatus": "ENABLED",  # One of 'ENABLED'|'DISABLED', it's enabled by default
            "PointInTimeRecoveryDescription": {
                "PointInTimeRecoveryStatus": "DISABLED"  # One of 'ENABLED'|'DISABLED'
            },
        }

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.table_arn
        elif attribute_name == "StreamArn" and self.stream_specification:
            return self.describe()["TableDescription"]["LatestStreamArn"]

        raise UnformattedGetAttTemplateException()

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def key_attributes(self):
        # A set of all the hash or range attributes for all indexes
        def keys_from_index(idx):
            schema = idx.schema
            return [attr["AttributeName"] for attr in schema]

        fieldnames = copy.copy(self.table_key_attrs)
        for idx in self.indexes + self.global_indexes:
            fieldnames += keys_from_index(idx)
        return fieldnames

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
        params = {}

        if "KeySchema" in properties:
            params["schema"] = properties["KeySchema"]
        if "AttributeDefinitions" in properties:
            params["attr"] = properties["AttributeDefinitions"]
        if "GlobalSecondaryIndexes" in properties:
            params["global_indexes"] = properties["GlobalSecondaryIndexes"]
        if "ProvisionedThroughput" in properties:
            params["throughput"] = properties["ProvisionedThroughput"]
        if "LocalSecondaryIndexes" in properties:
            params["indexes"] = properties["LocalSecondaryIndexes"]
        if "StreamSpecification" in properties:
            params["streams"] = properties["StreamSpecification"]

        table = dynamodb_backends[region_name].create_table(
            name=resource_name, **params
        )
        return table

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        table = dynamodb_backends[region_name].delete_table(name=resource_name)
        return table

    def _generate_arn(self, name):
        return "arn:aws:dynamodb:us-east-1:123456789011:table/" + name

    def set_stream_specification(self, streams):
        self.stream_specification = streams
        if streams and (streams.get("StreamEnabled") or streams.get("StreamViewType")):
            self.stream_specification["StreamEnabled"] = True
            self.latest_stream_label = datetime.datetime.utcnow().isoformat()
            self.stream_shard = StreamShard(self)
        else:
            self.stream_specification = {"StreamEnabled": False}
            self.latest_stream_label = None
            self.stream_shard = None

    def describe(self, base_key="TableDescription"):
        results = {
            base_key: {
                "AttributeDefinitions": self.attr,
                "ProvisionedThroughput": self.throughput,
                "TableSizeBytes": 0,
                "TableName": self.name,
                "TableStatus": "ACTIVE",
                "TableArn": self.table_arn,
                "KeySchema": self.schema,
                "ItemCount": len(self),
                "CreationDateTime": unix_time(self.created_at),
                "GlobalSecondaryIndexes": [
                    index.describe() for index in self.global_indexes
                ],
                "LocalSecondaryIndexes": [index.describe() for index in self.indexes],
            }
        }
        if self.stream_specification and self.stream_specification["StreamEnabled"]:
            results[base_key]["StreamSpecification"] = self.stream_specification
            if self.latest_stream_label:
                results[base_key]["LatestStreamLabel"] = self.latest_stream_label
                results[base_key]["LatestStreamArn"] = (
                    self.table_arn + "/stream/" + self.latest_stream_label
                )
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
            for key in index.schema:
                if key["KeyType"] == "HASH":
                    hash_key = key["AttributeName"]
            keys.append(hash_key)
        return keys

    @property
    def range_key_names(self):
        keys = [self.range_key_attr]
        for index in self.global_indexes:
            range_key = None
            for key in index.schema:
                if key["KeyType"] == "RANGE":
                    range_key = keys.append(key["AttributeName"])
            keys.append(range_key)
        return keys

    def put_item(
        self,
        item_attrs,
        expected=None,
        condition_expression=None,
        expression_attribute_names=None,
        expression_attribute_values=None,
        overwrite=False,
    ):
        if self.hash_key_attr not in item_attrs.keys():
            raise KeyError(
                "One or more parameter values were invalid: Missing the key "
                + self.hash_key_attr
                + " in the item"
            )
        hash_value = DynamoType(item_attrs.get(self.hash_key_attr))
        if self.has_range_key:
            if self.range_key_attr not in item_attrs.keys():
                raise KeyError(
                    "One or more parameter values were invalid: Missing the key "
                    + self.range_key_attr
                    + " in the item"
                )
            range_value = DynamoType(item_attrs.get(self.range_key_attr))
        else:
            range_value = None

        if expected is None:
            expected = {}
            lookup_range_value = range_value
        else:
            expected_range_value = expected.get(self.range_key_attr, {}).get("Value")
            if expected_range_value is None:
                lookup_range_value = range_value
            else:
                lookup_range_value = DynamoType(expected_range_value)
        current = self.get_item(hash_value, lookup_range_value)
        item = Item(
            hash_value, self.hash_key_type, range_value, self.range_key_type, item_attrs
        )

        if not overwrite:
            if not get_expected(expected).expr(current):
                raise ConditionalCheckFailed
            condition_op = get_filter_expression(
                condition_expression,
                expression_attribute_names,
                expression_attribute_values,
            )
            if not condition_op.expr(current):
                raise ConditionalCheckFailed

        if range_value:
            self.items[hash_value][range_value] = item
        else:
            self.items[hash_value] = item

        if self.stream_shard is not None:
            self.stream_shard.add(current, item)

        return item

    def __nonzero__(self):
        return True

    def __bool__(self):
        return self.__nonzero__()

    @property
    def has_range_key(self):
        return self.range_key_attr is not None

    def get_item(self, hash_key, range_key=None, projection_expression=None):
        if self.has_range_key and not range_key:
            raise ValueError(
                "Table has a range key, but no range key was passed into get_item"
            )
        try:
            result = None

            if range_key:
                result = self.items[hash_key][range_key]
            elif hash_key in self.items:
                result = self.items[hash_key]

            if projection_expression and result:
                result = copy.deepcopy(result)
                result.filter(projection_expression)

            if not result:
                raise KeyError

            return result
        except KeyError:
            return None

    def delete_item(self, hash_key, range_key):
        try:
            if range_key:
                item = self.items[hash_key].pop(range_key)
            else:
                item = self.items.pop(hash_key)

            if self.stream_shard is not None:
                self.stream_shard.add(item, None)

            return item
        except KeyError:
            return None

    def query(
        self,
        hash_key,
        range_comparison,
        range_objs,
        limit,
        exclusive_start_key,
        scan_index_forward,
        projection_expression,
        index_name=None,
        filter_expression=None,
        **filter_kwargs
    ):
        results = []

        if index_name:
            all_indexes = self.all_indexes()
            indexes_by_name = dict((i.name, i) for i in all_indexes)
            if index_name not in indexes_by_name:
                raise ValueError(
                    "Invalid index: %s for table: %s. Available indexes are: %s"
                    % (index_name, self.name, ", ".join(indexes_by_name.keys()))
                )

            index = indexes_by_name[index_name]
            try:
                index_hash_key = [
                    key for key in index.schema if key["KeyType"] == "HASH"
                ][0]
            except IndexError:
                raise ValueError("Missing Hash Key. KeySchema: %s" % index.name)

            try:
                index_range_key = [
                    key for key in index.schema if key["KeyType"] == "RANGE"
                ][0]
            except IndexError:
                index_range_key = None

            possible_results = []
            for item in self.all_items():
                if not isinstance(item, Item):
                    continue
                item_hash_key = item.attrs.get(index_hash_key["AttributeName"])
                if index_range_key is None:
                    if item_hash_key and item_hash_key == hash_key:
                        possible_results.append(item)
                else:
                    item_range_key = item.attrs.get(index_range_key["AttributeName"])
                    if item_hash_key and item_hash_key == hash_key and item_range_key:
                        possible_results.append(item)
        else:
            possible_results = [
                item
                for item in list(self.all_items())
                if isinstance(item, Item) and item.hash_key == hash_key
            ]
        if range_comparison:
            if index_name and not index_range_key:
                raise ValueError(
                    "Range Key comparison but no range key found for index: %s"
                    % index_name
                )

            elif index_name:
                for result in possible_results:
                    if result.attrs.get(index_range_key["AttributeName"]).compare(
                        range_comparison, range_objs
                    ):
                        results.append(result)
            else:
                for result in possible_results:
                    if result.range_key.compare(range_comparison, range_objs):
                        results.append(result)

        if filter_kwargs:
            for result in possible_results:
                for field, value in filter_kwargs.items():
                    dynamo_types = [
                        DynamoType(ele) for ele in value["AttributeValueList"]
                    ]
                    if result.attrs.get(field).compare(
                        value["ComparisonOperator"], dynamo_types
                    ):
                        results.append(result)

        if not range_comparison and not filter_kwargs:
            # If we're not filtering on range key or on an index return all
            # values
            results = possible_results

        if index_name:

            if index_range_key:

                # Convert to float if necessary to ensure proper ordering
                def conv(x):
                    return float(x.value) if x.type == "N" else x.value

                results.sort(
                    key=lambda item: conv(item.attrs[index_range_key["AttributeName"]])
                    if item.attrs.get(index_range_key["AttributeName"])
                    else None
                )
        else:
            results.sort(key=lambda item: item.range_key)

        if scan_index_forward is False:
            results.reverse()

        scanned_count = len(list(self.all_items()))

        if filter_expression is not None:
            results = [item for item in results if filter_expression.expr(item)]

        results = copy.deepcopy(results)
        if index_name:
            index = self.get_index(index_name)
            for result in results:
                index.project(result)
        if projection_expression:
            for result in results:
                result.filter(projection_expression)

        results, last_evaluated_key = self._trim_results(
            results, limit, exclusive_start_key
        )
        return results, scanned_count, last_evaluated_key

    def all_items(self):
        for hash_set in self.items.values():
            if self.range_key_attr:
                for item in hash_set.values():
                    yield item
            else:
                yield hash_set

    def all_indexes(self):
        return (self.global_indexes or []) + (self.indexes or [])

    def get_index(self, index_name, err=None):
        all_indexes = self.all_indexes()
        indexes_by_name = dict((i.name, i) for i in all_indexes)
        if err and index_name not in indexes_by_name:
            raise err
        return indexes_by_name[index_name]

    def has_idx_items(self, index_name):

        idx = self.get_index(index_name)
        idx_col_set = set([i["AttributeName"] for i in idx.schema])

        for hash_set in self.items.values():
            if self.range_key_attr:
                for item in hash_set.values():
                    if idx_col_set.issubset(set(item.attrs)):
                        yield item
            else:
                if idx_col_set.issubset(set(hash_set.attrs)):
                    yield hash_set

    def scan(
        self,
        filters,
        limit,
        exclusive_start_key,
        filter_expression=None,
        index_name=None,
        projection_expression=None,
    ):
        results = []
        scanned_count = 0

        if index_name:
            err = InvalidIndexNameError(
                "The table does not have the specified index: %s" % index_name
            )
            self.get_index(index_name, err)
            items = self.has_idx_items(index_name)
        else:
            items = self.all_items()

        for item in items:
            scanned_count += 1
            passes_all_conditions = True
            for (
                attribute_name,
                (comparison_operator, comparison_objs),
            ) in filters.items():
                attribute = item.attrs.get(attribute_name)

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

            if filter_expression is not None:
                passes_all_conditions &= filter_expression.expr(item)

            if passes_all_conditions:
                results.append(item)

        if projection_expression:
            results = copy.deepcopy(results)
            for result in results:
                result.filter(projection_expression)

        results, last_evaluated_key = self._trim_results(
            results, limit, exclusive_start_key, index_name
        )
        return results, scanned_count, last_evaluated_key

    def _trim_results(self, results, limit, exclusive_start_key, scanned_index=None):
        if exclusive_start_key is not None:
            hash_key = DynamoType(exclusive_start_key.get(self.hash_key_attr))
            range_key = exclusive_start_key.get(self.range_key_attr)
            if range_key is not None:
                range_key = DynamoType(range_key)
            for i in range(len(results)):
                if (
                    results[i].hash_key == hash_key
                    and results[i].range_key == range_key
                ):
                    results = results[i + 1 :]
                    break

        last_evaluated_key = None
        size_limit = 1000000  # DynamoDB has a 1MB size limit
        item_size = sum(res.size() for res in results)
        if item_size > size_limit:
            item_size = idx = 0
            while item_size + results[idx].size() < size_limit:
                item_size += results[idx].size()
                idx += 1
            limit = min(limit, idx) if limit else idx
        if limit and len(results) > limit:
            results = results[:limit]
            last_evaluated_key = {self.hash_key_attr: results[-1].hash_key}
            if results[-1].range_key is not None:
                last_evaluated_key[self.range_key_attr] = results[-1].range_key

            if scanned_index:
                idx = self.get_index(scanned_index)
                idx_col_list = [i["AttributeName"] for i in idx.schema]
                for col in idx_col_list:
                    last_evaluated_key[col] = results[-1].attrs[col]

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

    def delete(self, region_name):
        dynamodb_backends[region_name].delete_table(self.name)


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
                self.tables[table].tags = [
                    tag for tag in self.tables[table].tags if tag["Key"] not in tag_keys
                ]

    def list_tags_of_resource(self, table_arn):
        required_table = None
        for table in self.tables:
            if self.tables[table].table_arn == table_arn:
                required_table = self.tables[table]
        return required_table.tags

    def list_tables(self, limit, exclusive_start_table_name):
        all_tables = list(self.tables.keys())

        if exclusive_start_table_name:
            try:
                last_table_index = all_tables.index(exclusive_start_table_name)
            except ValueError:
                start = len(all_tables)
            else:
                start = last_table_index + 1
        else:
            start = 0

        if limit:
            tables = all_tables[start : start + limit]
        else:
            tables = all_tables[start:]

        if limit and len(all_tables) > start + limit:
            return tables, tables[-1]
        return tables, None

    def describe_table(self, name):
        table = self.tables[name]
        return table.describe(base_key="Table")

    def update_table(self, name, global_index, throughput, stream_spec):
        table = self.get_table(name)
        if global_index:
            table = self.update_table_global_indexes(name, global_index)
        if throughput:
            table = self.update_table_throughput(name, throughput)
        if stream_spec:
            table = self.update_table_streams(name, stream_spec)
        return table

    def update_table_throughput(self, name, throughput):
        table = self.tables[name]
        table.throughput = throughput
        return table

    def update_table_streams(self, name, stream_specification):
        table = self.tables[name]
        if (
            stream_specification.get("StreamEnabled")
            or stream_specification.get("StreamViewType")
        ) and table.latest_stream_label:
            raise ValueError("Table already has stream enabled")
        table.set_stream_specification(stream_specification)
        return table

    def update_table_global_indexes(self, name, global_index_updates):
        table = self.tables[name]
        gsis_by_name = dict((i.name, i) for i in table.global_indexes)
        for gsi_update in global_index_updates:
            gsi_to_create = gsi_update.get("Create")
            gsi_to_update = gsi_update.get("Update")
            gsi_to_delete = gsi_update.get("Delete")

            if gsi_to_delete:
                index_name = gsi_to_delete["IndexName"]
                if index_name not in gsis_by_name:
                    raise ValueError(
                        "Global Secondary Index does not exist, but tried to delete: %s"
                        % gsi_to_delete["IndexName"]
                    )

                del gsis_by_name[index_name]

            if gsi_to_update:
                index_name = gsi_to_update["IndexName"]
                if index_name not in gsis_by_name:
                    raise ValueError(
                        "Global Secondary Index does not exist, but tried to update: %s"
                        % index_name
                    )
                gsis_by_name[index_name].update(gsi_to_update)

            if gsi_to_create:
                if gsi_to_create["IndexName"] in gsis_by_name:
                    raise ValueError(
                        "Global Secondary Index already exists: %s"
                        % gsi_to_create["IndexName"]
                    )

                gsis_by_name[gsi_to_create["IndexName"]] = GlobalSecondaryIndex.create(
                    gsi_to_create, table.table_key_attrs,
                )

        # in python 3.6, dict.values() returns a dict_values object, but we expect it to be a list in other
        # parts of the codebase
        table.global_indexes = list(gsis_by_name.values())
        return table

    def put_item(
        self,
        table_name,
        item_attrs,
        expected=None,
        condition_expression=None,
        expression_attribute_names=None,
        expression_attribute_values=None,
        overwrite=False,
    ):
        table = self.tables.get(table_name)
        if not table:
            return None
        return table.put_item(
            item_attrs,
            expected,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
            overwrite,
        )

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
        if table.hash_key_attr not in keys or (
            table.has_range_key and table.range_key_attr not in keys
        ):
            raise ValueError(
                "Table has a range key, but no range key was passed into get_item"
            )
        hash_key = DynamoType(keys[table.hash_key_attr])
        range_key = (
            DynamoType(keys[table.range_key_attr]) if table.has_range_key else None
        )
        return hash_key, range_key

    def get_table(self, table_name):
        return self.tables.get(table_name)

    def get_item(self, table_name, keys, projection_expression=None):
        table = self.get_table(table_name)
        if not table:
            raise ValueError("No table found")
        hash_key, range_key = self.get_keys_value(table, keys)
        return table.get_item(hash_key, range_key, projection_expression)

    def query(
        self,
        table_name,
        hash_key_dict,
        range_comparison,
        range_value_dicts,
        limit,
        exclusive_start_key,
        scan_index_forward,
        projection_expression,
        index_name=None,
        expr_names=None,
        expr_values=None,
        filter_expression=None,
        **filter_kwargs
    ):
        table = self.tables.get(table_name)
        if not table:
            return None, None

        hash_key = DynamoType(hash_key_dict)
        range_values = [DynamoType(range_value) for range_value in range_value_dicts]

        filter_expression = get_filter_expression(
            filter_expression, expr_names, expr_values
        )

        return table.query(
            hash_key,
            range_comparison,
            range_values,
            limit,
            exclusive_start_key,
            scan_index_forward,
            projection_expression,
            index_name,
            filter_expression,
            **filter_kwargs
        )

    def scan(
        self,
        table_name,
        filters,
        limit,
        exclusive_start_key,
        filter_expression,
        expr_names,
        expr_values,
        index_name,
        projection_expression,
    ):
        table = self.tables.get(table_name)
        if not table:
            return None, None, None

        scan_filters = {}
        for key, (comparison_operator, comparison_values) in filters.items():
            dynamo_types = [DynamoType(value) for value in comparison_values]
            scan_filters[key] = (comparison_operator, dynamo_types)

        filter_expression = get_filter_expression(
            filter_expression, expr_names, expr_values
        )

        projection_expression = ",".join(
            [
                expr_names.get(attr, attr)
                for attr in projection_expression.replace(" ", "").split(",")
            ]
        )

        return table.scan(
            scan_filters,
            limit,
            exclusive_start_key,
            filter_expression,
            index_name,
            projection_expression,
        )

    def update_item(
        self,
        table_name,
        key,
        update_expression,
        expression_attribute_names,
        expression_attribute_values,
        attribute_updates=None,
        expected=None,
        condition_expression=None,
    ):
        table = self.get_table(table_name)

        # Support spaces between operators in an update expression
        # E.g. `a = b + c` -> `a=b+c`
        if update_expression:
            # Parse expression to get validation errors
            update_expression_ast = UpdateExpressionParser.make(update_expression)
            update_expression = re.sub(r"\s*([=\+-])\s*", "\\1", update_expression)

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
        orig_item = copy.deepcopy(item)

        if not expected:
            expected = {}

        if not get_expected(expected).expr(item):
            raise ConditionalCheckFailed
        condition_op = get_filter_expression(
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
        )
        if not condition_op.expr(item):
            raise ConditionalCheckFailed

        # Update does not fail on new items, so create one
        if item is None:
            data = {table.hash_key_attr: {hash_value.type: hash_value.value}}
            if range_value:
                data.update(
                    {table.range_key_attr: {range_value.type: range_value.value}}
                )

            table.put_item(data)
            item = table.get_item(hash_value, range_value)

        if attribute_updates:
            item.validate_no_empty_key_values(attribute_updates, table.key_attributes)

        if update_expression:
            validated_ast = UpdateExpressionValidator(
                update_expression_ast,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
                item=item,
                table=table,
            ).validate()
            try:
                UpdateExpressionExecutor(
                    validated_ast, item, expression_attribute_names
                ).execute()
            except ItemSizeTooLarge:
                raise ItemSizeToUpdateTooLarge()
        else:
            item.update_with_attribute_updates(attribute_updates)
        if table.stream_shard is not None:
            table.stream_shard.add(orig_item, item)
        return item

    def delete_item(
        self,
        table_name,
        key,
        expression_attribute_names=None,
        expression_attribute_values=None,
        condition_expression=None,
    ):
        table = self.get_table(table_name)
        if not table:
            return None

        hash_value, range_value = self.get_keys_value(table, key)
        item = table.get_item(hash_value, range_value)

        condition_op = get_filter_expression(
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
        )
        if not condition_op.expr(item):
            raise ConditionalCheckFailed

        return table.delete_item(hash_value, range_value)

    def update_time_to_live(self, table_name, ttl_spec):
        table = self.tables.get(table_name)
        if table is None:
            raise JsonRESTError("ResourceNotFound", "Table not found")

        if "Enabled" not in ttl_spec or "AttributeName" not in ttl_spec:
            raise JsonRESTError(
                "InvalidParameterValue",
                "TimeToLiveSpecification does not contain Enabled and AttributeName",
            )

        if ttl_spec["Enabled"]:
            table.ttl["TimeToLiveStatus"] = "ENABLED"
        else:
            table.ttl["TimeToLiveStatus"] = "DISABLED"
        table.ttl["AttributeName"] = ttl_spec["AttributeName"]

    def describe_time_to_live(self, table_name):
        table = self.tables.get(table_name)
        if table is None:
            raise JsonRESTError("ResourceNotFound", "Table not found")

        return table.ttl

    def transact_write_items(self, transact_items):
        # Create a backup in case any of the transactions fail
        original_table_state = copy.deepcopy(self.tables)
        errors = []
        for item in transact_items:
            try:
                if "ConditionCheck" in item:
                    item = item["ConditionCheck"]
                    key = item["Key"]
                    table_name = item["TableName"]
                    condition_expression = item.get("ConditionExpression", None)
                    expression_attribute_names = item.get(
                        "ExpressionAttributeNames", None
                    )
                    expression_attribute_values = item.get(
                        "ExpressionAttributeValues", None
                    )
                    current = self.get_item(table_name, key)

                    condition_op = get_filter_expression(
                        condition_expression,
                        expression_attribute_names,
                        expression_attribute_values,
                    )
                    if not condition_op.expr(current):
                        raise ConditionalCheckFailed()
                elif "Put" in item:
                    item = item["Put"]
                    attrs = item["Item"]
                    table_name = item["TableName"]
                    condition_expression = item.get("ConditionExpression", None)
                    expression_attribute_names = item.get(
                        "ExpressionAttributeNames", None
                    )
                    expression_attribute_values = item.get(
                        "ExpressionAttributeValues", None
                    )
                    self.put_item(
                        table_name,
                        attrs,
                        condition_expression=condition_expression,
                        expression_attribute_names=expression_attribute_names,
                        expression_attribute_values=expression_attribute_values,
                    )
                elif "Delete" in item:
                    item = item["Delete"]
                    key = item["Key"]
                    table_name = item["TableName"]
                    condition_expression = item.get("ConditionExpression", None)
                    expression_attribute_names = item.get(
                        "ExpressionAttributeNames", None
                    )
                    expression_attribute_values = item.get(
                        "ExpressionAttributeValues", None
                    )
                    self.delete_item(
                        table_name,
                        key,
                        condition_expression=condition_expression,
                        expression_attribute_names=expression_attribute_names,
                        expression_attribute_values=expression_attribute_values,
                    )
                elif "Update" in item:
                    item = item["Update"]
                    key = item["Key"]
                    table_name = item["TableName"]
                    update_expression = item["UpdateExpression"]
                    condition_expression = item.get("ConditionExpression", None)
                    expression_attribute_names = item.get(
                        "ExpressionAttributeNames", None
                    )
                    expression_attribute_values = item.get(
                        "ExpressionAttributeValues", None
                    )
                    self.update_item(
                        table_name,
                        key,
                        update_expression=update_expression,
                        condition_expression=condition_expression,
                        expression_attribute_names=expression_attribute_names,
                        expression_attribute_values=expression_attribute_values,
                    )
                else:
                    raise ValueError
                errors.append(None)
            except Exception as e:  # noqa: E722 Do not use bare except
                errors.append(type(e).__name__)
        if any(errors):
            # Rollback to the original state, and reraise the errors
            self.tables = original_table_state
            raise TransactionCanceledException(errors)

    def describe_continuous_backups(self, table_name):
        table = self.get_table(table_name)

        return table.continuous_backups

    def update_continuous_backups(self, table_name, point_in_time_spec):
        table = self.get_table(table_name)

        if (
            point_in_time_spec["PointInTimeRecoveryEnabled"]
            and table.continuous_backups["PointInTimeRecoveryDescription"][
                "PointInTimeRecoveryStatus"
            ]
            == "DISABLED"
        ):
            table.continuous_backups["PointInTimeRecoveryDescription"] = {
                "PointInTimeRecoveryStatus": "ENABLED",
                "EarliestRestorableDateTime": unix_time(),
                "LatestRestorableDateTime": unix_time(),
            }
        elif not point_in_time_spec["PointInTimeRecoveryEnabled"]:
            table.continuous_backups["PointInTimeRecoveryDescription"] = {
                "PointInTimeRecoveryStatus": "DISABLED"
            }

        return table.continuous_backups

    ######################
    # LIST of methods where the logic completely resides in responses.py
    # Duplicated here so that the implementation coverage script is aware
    # TODO: Move logic here
    ######################

    def batch_get_item(self):
        pass

    def batch_write_item(self):
        pass

    def transact_get_items(self):
        pass


dynamodb_backends = {}
for region in Session().get_available_regions("dynamodb"):
    dynamodb_backends[region] = DynamoDBBackend(region)
for region in Session().get_available_regions("dynamodb", partition_name="aws-us-gov"):
    dynamodb_backends[region] = DynamoDBBackend(region)
for region in Session().get_available_regions("dynamodb", partition_name="aws-cn"):
    dynamodb_backends[region] = DynamoDBBackend(region)
