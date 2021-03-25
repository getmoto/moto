from __future__ import unicode_literals

import copy
import json
import re

import itertools
import six

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores, amz_crc32, amzn_request_id
from .exceptions import (
    InvalidIndexNameError,
    ItemSizeTooLarge,
    MockValidationException,
    TransactionCanceledException,
)
from moto.dynamodb2.models import dynamodb_backends, dynamo_json_dump


TRANSACTION_MAX_ITEMS = 25


def put_has_empty_keys(field_updates, table):
    if table:
        key_names = table.key_attributes

        # string/binary fields with empty string as value
        empty_str_fields = [
            key
            for (key, val) in field_updates.items()
            if next(iter(val.keys())) in ["S", "B"] and next(iter(val.values())) == ""
        ]
        return any([keyname in empty_str_fields for keyname in key_names])
    return False


def get_empty_str_error():
    er = "com.amazonaws.dynamodb.v20111205#ValidationException"
    return (
        400,
        {"server": "amazon.com"},
        dynamo_json_dump(
            {
                "__type": er,
                "message": (
                    "One or more parameter values were "
                    "invalid: An AttributeValue may not "
                    "contain an empty string"
                ),
            }
        ),
    )


class DynamoHandler(BaseResponse):
    def get_endpoint_name(self, headers):
        """Parses request headers and extracts part od the X-Amz-Target
        that corresponds to a method of DynamoHandler

        ie: X-Amz-Target: DynamoDB_20111205.ListTables -> ListTables
        """
        # Headers are case-insensitive. Probably a better way to do this.
        match = headers.get("x-amz-target") or headers.get("X-Amz-Target")
        if match:
            return match.split(".")[1]

    def error(self, type_, message, status=400):
        return (
            status,
            self.response_headers,
            dynamo_json_dump({"__type": type_, "message": message}),
        )

    @property
    def dynamodb_backend(self):
        """
        :return: DynamoDB2 Backend
        :rtype: moto.dynamodb2.models.DynamoDBBackend
        """
        return dynamodb_backends[self.region]

    @amz_crc32
    @amzn_request_id
    def call_action(self):
        self.body = json.loads(self.body or "{}")
        endpoint = self.get_endpoint_name(self.headers)
        if endpoint:
            endpoint = camelcase_to_underscores(endpoint)
            response = getattr(self, endpoint)()
            if isinstance(response, six.string_types):
                return 200, self.response_headers, response

            else:
                status_code, new_headers, response_content = response
                self.response_headers.update(new_headers)
                return status_code, self.response_headers, response_content
        else:
            return 404, self.response_headers, ""

    def list_tables(self):
        body = self.body
        limit = body.get("Limit", 100)
        exclusive_start_table_name = body.get("ExclusiveStartTableName")
        tables, last_eval = self.dynamodb_backend.list_tables(
            limit, exclusive_start_table_name
        )

        response = {"TableNames": tables}
        if last_eval:
            response["LastEvaluatedTableName"] = last_eval

        return dynamo_json_dump(response)

    def create_table(self):
        body = self.body
        # get the table name
        table_name = body["TableName"]
        # check billing mode and get the throughput
        if "BillingMode" in body.keys() and body["BillingMode"] == "PAY_PER_REQUEST":
            if "ProvisionedThroughput" in body.keys():
                er = "com.amazonaws.dynamodb.v20111205#ValidationException"
                return self.error(
                    er,
                    "ProvisionedThroughput cannot be specified \
                                   when BillingMode is PAY_PER_REQUEST",
                )
            throughput = None
        else:  # Provisioned (default billing mode)
            throughput = body.get("ProvisionedThroughput")
        # getting the schema
        key_schema = body["KeySchema"]
        # getting attribute definition
        attr = body["AttributeDefinitions"]
        # getting the indexes
        global_indexes = body.get("GlobalSecondaryIndexes", [])
        local_secondary_indexes = body.get("LocalSecondaryIndexes", [])
        # Verify AttributeDefinitions list all
        expected_attrs = []
        expected_attrs.extend([key["AttributeName"] for key in key_schema])
        expected_attrs.extend(
            schema["AttributeName"]
            for schema in itertools.chain(
                *list(idx["KeySchema"] for idx in local_secondary_indexes)
            )
        )
        expected_attrs.extend(
            schema["AttributeName"]
            for schema in itertools.chain(
                *list(idx["KeySchema"] for idx in global_indexes)
            )
        )
        expected_attrs = list(set(expected_attrs))
        expected_attrs.sort()
        actual_attrs = [item["AttributeName"] for item in attr]
        actual_attrs.sort()
        if actual_attrs != expected_attrs:
            er = "com.amazonaws.dynamodb.v20111205#ValidationException"
            return self.error(
                er,
                "One or more parameter values were invalid: "
                "Some index key attributes are not defined in AttributeDefinitions. "
                "Keys: "
                + str(expected_attrs)
                + ", AttributeDefinitions: "
                + str(actual_attrs),
            )
        # get the stream specification
        streams = body.get("StreamSpecification")

        table = self.dynamodb_backend.create_table(
            table_name,
            schema=key_schema,
            throughput=throughput,
            attr=attr,
            global_indexes=global_indexes,
            indexes=local_secondary_indexes,
            streams=streams,
        )
        if table is not None:
            return dynamo_json_dump(table.describe())
        else:
            er = "com.amazonaws.dynamodb.v20111205#ResourceInUseException"
            return self.error(er, "Resource in use")

    def delete_table(self):
        name = self.body["TableName"]
        table = self.dynamodb_backend.delete_table(name)
        if table is not None:
            return dynamo_json_dump(table.describe())
        else:
            er = "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"
            return self.error(er, "Requested resource not found")

    def tag_resource(self):
        table_arn = self.body["ResourceArn"]
        tags = self.body["Tags"]
        self.dynamodb_backend.tag_resource(table_arn, tags)
        return ""

    def untag_resource(self):
        table_arn = self.body["ResourceArn"]
        tags = self.body["TagKeys"]
        self.dynamodb_backend.untag_resource(table_arn, tags)
        return ""

    def list_tags_of_resource(self):
        try:
            table_arn = self.body["ResourceArn"]
            all_tags = self.dynamodb_backend.list_tags_of_resource(table_arn)
            all_tag_keys = [tag["Key"] for tag in all_tags]
            marker = self.body.get("NextToken")
            if marker:
                start = all_tag_keys.index(marker) + 1
            else:
                start = 0
            max_items = 10  # there is no default, but using 10 to make testing easier
            tags_resp = all_tags[start : start + max_items]
            next_marker = None
            if len(all_tags) > start + max_items:
                next_marker = tags_resp[-1]["Key"]
            if next_marker:
                return json.dumps({"Tags": tags_resp, "NextToken": next_marker})
            return json.dumps({"Tags": tags_resp})
        except AttributeError:
            er = "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"
            return self.error(er, "Requested resource not found")

    def update_table(self):
        name = self.body["TableName"]
        global_index = self.body.get("GlobalSecondaryIndexUpdates", None)
        throughput = self.body.get("ProvisionedThroughput", None)
        stream_spec = self.body.get("StreamSpecification", None)
        try:
            table = self.dynamodb_backend.update_table(
                name=name,
                global_index=global_index,
                throughput=throughput,
                stream_spec=stream_spec,
            )
            return dynamo_json_dump(table.describe())
        except ValueError:
            er = "com.amazonaws.dynamodb.v20111205#ResourceInUseException"
            return self.error(er, "Cannot enable stream")

    def describe_table(self):
        name = self.body["TableName"]
        try:
            table = self.dynamodb_backend.describe_table(name)
            return dynamo_json_dump(table)
        except KeyError:
            er = "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"
            return self.error(er, "Requested resource not found")

    def put_item(self):
        name = self.body["TableName"]
        item = self.body["Item"]
        return_values = self.body.get("ReturnValues", "NONE")

        if return_values not in ("ALL_OLD", "NONE"):
            er = "com.amazonaws.dynamodb.v20111205#ValidationException"
            return self.error(er, "Return values set to invalid value")

        if put_has_empty_keys(item, self.dynamodb_backend.get_table(name)):
            return get_empty_str_error()

        overwrite = "Expected" not in self.body
        if not overwrite:
            expected = self.body["Expected"]
        else:
            expected = None

        if return_values == "ALL_OLD":
            existing_item = self.dynamodb_backend.get_item(name, item)
            if existing_item:
                existing_attributes = existing_item.to_json()["Attributes"]
            else:
                existing_attributes = {}

        # Attempt to parse simple ConditionExpressions into an Expected
        # expression
        condition_expression = self.body.get("ConditionExpression")
        expression_attribute_names = self.body.get("ExpressionAttributeNames", {})
        expression_attribute_values = self.body.get("ExpressionAttributeValues", {})

        if condition_expression:
            overwrite = False

        try:
            result = self.dynamodb_backend.put_item(
                name,
                item,
                expected,
                condition_expression,
                expression_attribute_names,
                expression_attribute_values,
                overwrite,
            )
        except ItemSizeTooLarge:
            er = "com.amazonaws.dynamodb.v20111205#ValidationException"
            return self.error(er, ItemSizeTooLarge.item_size_too_large_msg)
        except KeyError as ke:
            er = "com.amazonaws.dynamodb.v20111205#ValidationException"
            return self.error(er, ke.args[0])
        except ValueError as ve:
            er = "com.amazonaws.dynamodb.v20111205#ConditionalCheckFailedException"
            return self.error(er, str(ve))

        if result:
            item_dict = result.to_json()
            item_dict["ConsumedCapacity"] = {"TableName": name, "CapacityUnits": 1}
            if return_values == "ALL_OLD":
                item_dict["Attributes"] = existing_attributes
            else:
                item_dict.pop("Attributes", None)
            return dynamo_json_dump(item_dict)
        else:
            er = "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"
            return self.error(er, "Requested resource not found")

    def batch_write_item(self):
        table_batches = self.body["RequestItems"]

        for table_name, table_requests in table_batches.items():
            for table_request in table_requests:
                request_type = list(table_request.keys())[0]
                request = list(table_request.values())[0]
                if request_type == "PutRequest":
                    item = request["Item"]
                    self.dynamodb_backend.put_item(table_name, item)
                elif request_type == "DeleteRequest":
                    keys = request["Key"]
                    item = self.dynamodb_backend.delete_item(table_name, keys)

        response = {
            "ConsumedCapacity": [
                {
                    "TableName": table_name,
                    "CapacityUnits": 1.0,
                    "Table": {"CapacityUnits": 1.0},
                }
                for table_name, table_requests in table_batches.items()
            ],
            "ItemCollectionMetrics": {},
            "UnprocessedItems": {},
        }

        return dynamo_json_dump(response)

    def get_item(self):
        name = self.body["TableName"]
        table = self.dynamodb_backend.get_table(name)
        if table is None:
            return self.error(
                "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
                "Requested resource not found",
            )
        key = self.body["Key"]
        projection_expression = self.body.get("ProjectionExpression")
        expression_attribute_names = self.body.get("ExpressionAttributeNames", {})

        projection_expression = self._adjust_projection_expression(
            projection_expression, expression_attribute_names
        )

        try:
            item = self.dynamodb_backend.get_item(name, key, projection_expression)
        except ValueError:
            er = "com.amazon.coral.validate#ValidationException"
            return self.error(er, "Validation Exception")
        if item:
            item_dict = item.describe_attrs(attributes=None)
            item_dict["ConsumedCapacity"] = {"TableName": name, "CapacityUnits": 0.5}
            return dynamo_json_dump(item_dict)
        else:
            # Item not found
            return 200, self.response_headers, "{}"

    def batch_get_item(self):
        table_batches = self.body["RequestItems"]

        results = {"ConsumedCapacity": [], "Responses": {}, "UnprocessedKeys": {}}

        # Validation: Can only request up to 100 items at the same time
        # Scenario 1: We're requesting more than a 100 keys from a single table
        for table_name, table_request in table_batches.items():
            if len(table_request["Keys"]) > 100:
                return self.error(
                    "com.amazonaws.dynamodb.v20111205#ValidationException",
                    "1 validation error detected: Value at 'requestItems."
                    + table_name
                    + ".member.keys' failed to satisfy constraint: Member must have length less than or equal to 100",
                )
        # Scenario 2: We're requesting more than a 100 keys across all tables
        nr_of_keys_across_all_tables = sum(
            [len(req["Keys"]) for _, req in table_batches.items()]
        )
        if nr_of_keys_across_all_tables > 100:
            return self.error(
                "com.amazonaws.dynamodb.v20111205#ValidationException",
                "Too many items requested for the BatchGetItem call",
            )

        for table_name, table_request in table_batches.items():
            keys = table_request["Keys"]
            if self._contains_duplicates(keys):
                er = "com.amazon.coral.validate#ValidationException"
                return self.error(er, "Provided list of item keys contains duplicates")
            attributes_to_get = table_request.get("AttributesToGet")
            projection_expression = table_request.get("ProjectionExpression")
            expression_attribute_names = table_request.get(
                "ExpressionAttributeNames", {}
            )

            projection_expression = self._adjust_projection_expression(
                projection_expression, expression_attribute_names
            )

            results["Responses"][table_name] = []
            for key in keys:
                item = self.dynamodb_backend.get_item(
                    table_name, key, projection_expression
                )
                if item:
                    item_describe = item.describe_attrs(attributes_to_get)
                    results["Responses"][table_name].append(item_describe["Item"])

            results["ConsumedCapacity"].append(
                {"CapacityUnits": len(keys), "TableName": table_name}
            )
        return dynamo_json_dump(results)

    def _contains_duplicates(self, keys):
        unique_keys = []
        for k in keys:
            if k in unique_keys:
                return True
            else:
                unique_keys.append(k)
        return False

    def query(self):
        name = self.body["TableName"]
        key_condition_expression = self.body.get("KeyConditionExpression")
        projection_expression = self.body.get("ProjectionExpression")
        expression_attribute_names = self.body.get("ExpressionAttributeNames", {})
        filter_expression = self.body.get("FilterExpression")
        expression_attribute_values = self.body.get("ExpressionAttributeValues", {})

        projection_expression = self._adjust_projection_expression(
            projection_expression, expression_attribute_names
        )

        filter_kwargs = {}

        if key_condition_expression:
            value_alias_map = self.body.get("ExpressionAttributeValues", {})

            table = self.dynamodb_backend.get_table(name)

            # If table does not exist
            if table is None:
                return self.error(
                    "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException",
                    "Requested resource not found",
                )

            index_name = self.body.get("IndexName")
            if index_name:
                all_indexes = (table.global_indexes or []) + (table.indexes or [])
                indexes_by_name = dict((i.name, i) for i in all_indexes)
                if index_name not in indexes_by_name:
                    er = "com.amazonaws.dynamodb.v20120810#ResourceNotFoundException"
                    return self.error(
                        er,
                        "Invalid index: {} for table: {}. Available indexes are: {}".format(
                            index_name, name, ", ".join(indexes_by_name.keys())
                        ),
                    )

                index = indexes_by_name[index_name].schema
            else:
                index = table.schema

            reverse_attribute_lookup = dict(
                (v, k)
                for k, v in six.iteritems(self.body.get("ExpressionAttributeNames", {}))
            )

            if " and " in key_condition_expression.lower():
                expressions = re.split(
                    " AND ", key_condition_expression, maxsplit=1, flags=re.IGNORECASE
                )

                index_hash_key = [key for key in index if key["KeyType"] == "HASH"][0]
                hash_key_var = reverse_attribute_lookup.get(
                    index_hash_key["AttributeName"], index_hash_key["AttributeName"]
                )
                hash_key_regex = r"(^|[\s(]){0}\b".format(hash_key_var)
                i, hash_key_expression = next(
                    (i, e)
                    for i, e in enumerate(expressions)
                    if re.search(hash_key_regex, e)
                )
                hash_key_expression = hash_key_expression.strip("()")
                expressions.pop(i)

                # TODO implement more than one range expression and OR operators
                range_key_expression = expressions[0].strip("()")
                range_key_expression_components = range_key_expression.split()
                range_comparison = range_key_expression_components[1]

                if " and " in range_key_expression.lower():
                    range_comparison = "BETWEEN"
                    range_values = [
                        value_alias_map[range_key_expression_components[2]],
                        value_alias_map[range_key_expression_components[4]],
                    ]
                elif "begins_with" in range_key_expression:
                    range_comparison = "BEGINS_WITH"
                    range_values = [
                        value_alias_map[range_key_expression_components[-1]]
                    ]
                elif "begins_with" in range_key_expression.lower():
                    function_used = range_key_expression[
                        range_key_expression.lower().index("begins_with") : len(
                            "begins_with"
                        )
                    ]
                    return self.error(
                        "com.amazonaws.dynamodb.v20111205#ValidationException",
                        "Invalid KeyConditionExpression: Invalid function name; function: {}".format(
                            function_used
                        ),
                    )
                else:
                    range_values = [value_alias_map[range_key_expression_components[2]]]
            else:
                hash_key_expression = key_condition_expression.strip("()")
                range_comparison = None
                range_values = []

            if "=" not in hash_key_expression:
                return self.error(
                    "com.amazonaws.dynamodb.v20111205#ValidationException",
                    "Query key condition not supported",
                )
            hash_key_value_alias = hash_key_expression.split("=")[1].strip()
            # Temporary fix until we get proper KeyConditionExpression function
            hash_key = value_alias_map.get(
                hash_key_value_alias, {"S": hash_key_value_alias}
            )
        else:
            # 'KeyConditions': {u'forum_name': {u'ComparisonOperator': u'EQ', u'AttributeValueList': [{u'S': u'the-key'}]}}
            key_conditions = self.body.get("KeyConditions")
            query_filters = self.body.get("QueryFilter")

            if not (key_conditions or query_filters):
                return self.error(
                    "com.amazonaws.dynamodb.v20111205#ValidationException",
                    "Either KeyConditions or QueryFilter should be present",
                )

            if key_conditions:
                (
                    hash_key_name,
                    range_key_name,
                ) = self.dynamodb_backend.get_table_keys_name(
                    name, key_conditions.keys()
                )
                for key, value in key_conditions.items():
                    if key not in (hash_key_name, range_key_name):
                        filter_kwargs[key] = value
                if hash_key_name is None:
                    er = "'com.amazonaws.dynamodb.v20120810#ResourceNotFoundException"
                    return self.error(er, "Requested resource not found")
                hash_key = key_conditions[hash_key_name]["AttributeValueList"][0]
                if len(key_conditions) == 1:
                    range_comparison = None
                    range_values = []
                else:
                    if range_key_name is None and not filter_kwargs:
                        er = "com.amazon.coral.validate#ValidationException"
                        return self.error(er, "Validation Exception")
                    else:
                        range_condition = key_conditions.get(range_key_name)
                        if range_condition:
                            range_comparison = range_condition["ComparisonOperator"]
                            range_values = range_condition["AttributeValueList"]
                        else:
                            range_comparison = None
                            range_values = []
            if query_filters:
                filter_kwargs.update(query_filters)
        index_name = self.body.get("IndexName")
        exclusive_start_key = self.body.get("ExclusiveStartKey")
        limit = self.body.get("Limit")
        scan_index_forward = self.body.get("ScanIndexForward")
        items, scanned_count, last_evaluated_key = self.dynamodb_backend.query(
            name,
            hash_key,
            range_comparison,
            range_values,
            limit,
            exclusive_start_key,
            scan_index_forward,
            projection_expression,
            index_name=index_name,
            expr_names=expression_attribute_names,
            expr_values=expression_attribute_values,
            filter_expression=filter_expression,
            **filter_kwargs
        )
        if items is None:
            er = "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"
            return self.error(er, "Requested resource not found")

        result = {
            "Count": len(items),
            "ConsumedCapacity": {"TableName": name, "CapacityUnits": 1},
            "ScannedCount": scanned_count,
        }

        if self.body.get("Select", "").upper() != "COUNT":
            result["Items"] = [item.attrs for item in items]

        if last_evaluated_key is not None:
            result["LastEvaluatedKey"] = last_evaluated_key

        return dynamo_json_dump(result)

    def _adjust_projection_expression(self, projection_expression, expr_attr_names):
        def _adjust(expression):
            return (
                expr_attr_names[expression]
                if expression in expr_attr_names
                else expression
            )

        if projection_expression and expr_attr_names:
            expressions = [x.strip() for x in projection_expression.split(",")]
            return ",".join(
                [
                    ".".join([_adjust(expr) for expr in nested_expr.split(".")])
                    for nested_expr in expressions
                ]
            )

        return projection_expression

    def scan(self):
        name = self.body["TableName"]

        filters = {}
        scan_filters = self.body.get("ScanFilter", {})
        for attribute_name, scan_filter in scan_filters.items():
            # Keys are attribute names. Values are tuples of (comparison,
            # comparison_value)
            comparison_operator = scan_filter["ComparisonOperator"]
            comparison_values = scan_filter.get("AttributeValueList", [])
            filters[attribute_name] = (comparison_operator, comparison_values)

        filter_expression = self.body.get("FilterExpression")
        expression_attribute_values = self.body.get("ExpressionAttributeValues", {})
        expression_attribute_names = self.body.get("ExpressionAttributeNames", {})
        projection_expression = self.body.get("ProjectionExpression", "")
        exclusive_start_key = self.body.get("ExclusiveStartKey")
        limit = self.body.get("Limit")
        index_name = self.body.get("IndexName")

        try:
            items, scanned_count, last_evaluated_key = self.dynamodb_backend.scan(
                name,
                filters,
                limit,
                exclusive_start_key,
                filter_expression,
                expression_attribute_names,
                expression_attribute_values,
                index_name,
                projection_expression,
            )
        except InvalidIndexNameError as err:
            er = "com.amazonaws.dynamodb.v20111205#ValidationException"
            return self.error(er, str(err))
        except ValueError as err:
            er = "com.amazonaws.dynamodb.v20111205#ValidationError"
            return self.error(er, "Bad Filter Expression: {0}".format(err))
        except Exception as err:
            er = "com.amazonaws.dynamodb.v20111205#InternalFailure"
            return self.error(er, "Internal error. {0}".format(err))

        # Items should be a list, at least an empty one. Is None if table does not exist.
        # Should really check this at the beginning
        if items is None:
            er = "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"
            return self.error(er, "Requested resource not found")

        result = {
            "Count": len(items),
            "Items": [item.attrs for item in items],
            "ConsumedCapacity": {"TableName": name, "CapacityUnits": 1},
            "ScannedCount": scanned_count,
        }
        if last_evaluated_key is not None:
            result["LastEvaluatedKey"] = last_evaluated_key
        return dynamo_json_dump(result)

    def delete_item(self):
        name = self.body["TableName"]
        key = self.body["Key"]
        return_values = self.body.get("ReturnValues", "NONE")
        if return_values not in ("ALL_OLD", "NONE"):
            er = "com.amazonaws.dynamodb.v20111205#ValidationException"
            return self.error(er, "Return values set to invalid value")

        table = self.dynamodb_backend.get_table(name)
        if not table:
            er = "com.amazonaws.dynamodb.v20120810#ConditionalCheckFailedException"
            return self.error(
                er, "A condition specified in the operation could not be evaluated."
            )

        # Attempt to parse simple ConditionExpressions into an Expected
        # expression
        condition_expression = self.body.get("ConditionExpression")
        expression_attribute_names = self.body.get("ExpressionAttributeNames", {})
        expression_attribute_values = self.body.get("ExpressionAttributeValues", {})

        try:
            item = self.dynamodb_backend.delete_item(
                name,
                key,
                expression_attribute_names,
                expression_attribute_values,
                condition_expression,
            )
        except ValueError:
            er = "com.amazonaws.dynamodb.v20111205#ConditionalCheckFailedException"
            return self.error(
                er, "A condition specified in the operation could not be evaluated."
            )

        if item and return_values == "ALL_OLD":
            item_dict = item.to_json()
        else:
            item_dict = {"Attributes": {}}
        item_dict["ConsumedCapacityUnits"] = 0.5
        return dynamo_json_dump(item_dict)

    def update_item(self):
        name = self.body["TableName"]
        key = self.body["Key"]
        return_values = self.body.get("ReturnValues", "NONE")
        update_expression = self.body.get("UpdateExpression", "").strip()
        attribute_updates = self.body.get("AttributeUpdates")
        expression_attribute_names = self.body.get("ExpressionAttributeNames", {})
        expression_attribute_values = self.body.get("ExpressionAttributeValues", {})
        # We need to copy the item in order to avoid it being modified by the update_item operation
        existing_item = copy.deepcopy(self.dynamodb_backend.get_item(name, key))
        if existing_item:
            existing_attributes = existing_item.to_json()["Attributes"]
        else:
            existing_attributes = {}

        if return_values not in (
            "NONE",
            "ALL_OLD",
            "ALL_NEW",
            "UPDATED_OLD",
            "UPDATED_NEW",
        ):
            er = "com.amazonaws.dynamodb.v20111205#ValidationException"
            return self.error(er, "Return values set to invalid value")

        if "Expected" in self.body:
            expected = self.body["Expected"]
        else:
            expected = None

        # Attempt to parse simple ConditionExpressions into an Expected
        # expression
        condition_expression = self.body.get("ConditionExpression")
        expression_attribute_names = self.body.get("ExpressionAttributeNames", {})
        expression_attribute_values = self.body.get("ExpressionAttributeValues", {})

        try:
            item = self.dynamodb_backend.update_item(
                name,
                key,
                update_expression=update_expression,
                attribute_updates=attribute_updates,
                expression_attribute_names=expression_attribute_names,
                expression_attribute_values=expression_attribute_values,
                expected=expected,
                condition_expression=condition_expression,
            )
        except MockValidationException as mve:
            er = "com.amazonaws.dynamodb.v20111205#ValidationException"
            return self.error(er, mve.exception_msg)
        except ValueError:
            er = "com.amazonaws.dynamodb.v20111205#ConditionalCheckFailedException"
            return self.error(
                er, "A condition specified in the operation could not be evaluated."
            )
        except TypeError:
            er = "com.amazonaws.dynamodb.v20111205#ValidationException"
            return self.error(er, "Validation Exception")

        item_dict = item.to_json()
        item_dict["ConsumedCapacity"] = {"TableName": name, "CapacityUnits": 0.5}
        unchanged_attributes = {
            k
            for k in existing_attributes.keys()
            if existing_attributes[k] == item_dict["Attributes"].get(k)
        }
        changed_attributes = (
            set(existing_attributes.keys())
            .union(item_dict["Attributes"].keys())
            .difference(unchanged_attributes)
        )

        if return_values == "NONE":
            item_dict["Attributes"] = {}
        elif return_values == "ALL_OLD":
            item_dict["Attributes"] = existing_attributes
        elif return_values == "UPDATED_OLD":
            item_dict["Attributes"] = {
                k: v for k, v in existing_attributes.items() if k in changed_attributes
            }
        elif return_values == "UPDATED_NEW":
            item_dict["Attributes"] = self._build_updated_new_attributes(
                existing_attributes, item_dict["Attributes"]
            )
        return dynamo_json_dump(item_dict)

    def _build_updated_new_attributes(self, original, changed):
        if type(changed) != type(original):
            return changed
        else:
            if type(changed) is dict:
                return {
                    key: self._build_updated_new_attributes(
                        original.get(key, None), changed[key]
                    )
                    for key in changed.keys()
                    if key not in original or changed[key] != original[key]
                }
            elif type(changed) in (set, list):
                if len(changed) != len(original):
                    return changed
                else:
                    return [
                        self._build_updated_new_attributes(
                            original[index], changed[index]
                        )
                        for index in range(len(changed))
                    ]
            else:
                return changed

    def describe_limits(self):
        return json.dumps(
            {
                "AccountMaxReadCapacityUnits": 20000,
                "TableMaxWriteCapacityUnits": 10000,
                "AccountMaxWriteCapacityUnits": 20000,
                "TableMaxReadCapacityUnits": 10000,
            }
        )

    def update_time_to_live(self):
        name = self.body["TableName"]
        ttl_spec = self.body["TimeToLiveSpecification"]

        self.dynamodb_backend.update_time_to_live(name, ttl_spec)

        return json.dumps({"TimeToLiveSpecification": ttl_spec})

    def describe_time_to_live(self):
        name = self.body["TableName"]

        ttl_spec = self.dynamodb_backend.describe_time_to_live(name)

        return json.dumps({"TimeToLiveDescription": ttl_spec})

    def transact_get_items(self):
        transact_items = self.body["TransactItems"]
        responses = list()

        if len(transact_items) > TRANSACTION_MAX_ITEMS:
            msg = "1 validation error detected: Value '["
            err_list = list()
            request_id = 268435456
            for _ in transact_items:
                request_id += 1
                hex_request_id = format(request_id, "x")
                err_list.append(
                    "com.amazonaws.dynamodb.v20120810.TransactGetItem@%s"
                    % hex_request_id
                )
            msg += ", ".join(err_list)
            msg += (
                "'] at 'transactItems' failed to satisfy constraint: "
                "Member must have length less than or equal to %s"
                % TRANSACTION_MAX_ITEMS
            )

            return self.error("ValidationException", msg)

        ret_consumed_capacity = self.body.get("ReturnConsumedCapacity", "NONE")
        consumed_capacity = dict()

        for transact_item in transact_items:

            table_name = transact_item["Get"]["TableName"]
            key = transact_item["Get"]["Key"]
            try:
                item = self.dynamodb_backend.get_item(table_name, key)
            except ValueError:
                er = "com.amazonaws.dynamodb.v20111205#ResourceNotFoundException"
                return self.error(er, "Requested resource not found")

            if not item:
                responses.append({})
                continue

            item_describe = item.describe_attrs(False)
            responses.append(item_describe)

            table_capacity = consumed_capacity.get(table_name, {})
            table_capacity["TableName"] = table_name
            capacity_units = table_capacity.get("CapacityUnits", 0) + 2.0
            table_capacity["CapacityUnits"] = capacity_units
            read_capacity_units = table_capacity.get("ReadCapacityUnits", 0) + 2.0
            table_capacity["ReadCapacityUnits"] = read_capacity_units
            consumed_capacity[table_name] = table_capacity

            if ret_consumed_capacity == "INDEXES":
                table_capacity["Table"] = {
                    "CapacityUnits": capacity_units,
                    "ReadCapacityUnits": read_capacity_units,
                }

        result = dict()
        result.update({"Responses": responses})
        if ret_consumed_capacity != "NONE":
            result.update({"ConsumedCapacity": [v for v in consumed_capacity.values()]})

        return dynamo_json_dump(result)

    def transact_write_items(self):
        transact_items = self.body["TransactItems"]
        try:
            self.dynamodb_backend.transact_write_items(transact_items)
        except TransactionCanceledException as e:
            er = "com.amazonaws.dynamodb.v20111205#TransactionCanceledException"
            return self.error(er, str(e))
        response = {"ConsumedCapacity": [], "ItemCollectionMetrics": {}}
        return dynamo_json_dump(response)

    def describe_continuous_backups(self):
        name = self.body["TableName"]

        if self.dynamodb_backend.get_table(name) is None:
            return self.error(
                "com.amazonaws.dynamodb.v20111205#TableNotFoundException",
                "Table not found: {}".format(name),
            )

        response = self.dynamodb_backend.describe_continuous_backups(name)

        return json.dumps({"ContinuousBackupsDescription": response})

    def update_continuous_backups(self):
        name = self.body["TableName"]
        point_in_time_spec = self.body["PointInTimeRecoverySpecification"]

        if self.dynamodb_backend.get_table(name) is None:
            return self.error(
                "com.amazonaws.dynamodb.v20111205#TableNotFoundException",
                "Table not found: {}".format(name),
            )

        response = self.dynamodb_backend.update_continuous_backups(
            name, point_in_time_spec
        )

        return json.dumps({"ContinuousBackupsDescription": response})
