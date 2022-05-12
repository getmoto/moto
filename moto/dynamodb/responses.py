import copy
import json
import re

import itertools
from functools import wraps

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores, amz_crc32, amzn_request_id
from .exceptions import (
    MockValidationException,
    ResourceNotFoundException,
    ConditionalCheckFailed,
)
from moto.dynamodb.models import dynamodb_backends, dynamo_json_dump


TRANSACTION_MAX_ITEMS = 25


def include_consumed_capacity(val=1.0):
    def _inner(f):
        @wraps(f)
        def _wrapper(*args, **kwargs):
            (handler,) = args
            expected_capacity = handler.body.get("ReturnConsumedCapacity", "NONE")
            if expected_capacity not in ["NONE", "TOTAL", "INDEXES"]:
                type_ = "ValidationException"
                message = "1 validation error detected: Value '{}' at 'returnConsumedCapacity' failed to satisfy constraint: Member must satisfy enum value set: [INDEXES, TOTAL, NONE]".format(
                    expected_capacity
                )
                return (
                    400,
                    handler.response_headers,
                    dynamo_json_dump({"__type": type_, "message": message}),
                )
            table_name = handler.body.get("TableName", "")
            index_name = handler.body.get("IndexName", None)

            response = f(*args, **kwargs)

            if isinstance(response, str):
                body = json.loads(response)

                if expected_capacity == "TOTAL":
                    body["ConsumedCapacity"] = {
                        "TableName": table_name,
                        "CapacityUnits": val,
                    }
                elif expected_capacity == "INDEXES":
                    body["ConsumedCapacity"] = {
                        "TableName": table_name,
                        "CapacityUnits": val,
                        "Table": {"CapacityUnits": val},
                    }
                    if index_name:
                        body["ConsumedCapacity"]["LocalSecondaryIndexes"] = {
                            index_name: {"CapacityUnits": val}
                        }

                return dynamo_json_dump(body)

            return response

        return _wrapper

    return _inner


def put_has_empty_keys(field_updates, table):
    if table:
        key_names = table.attribute_keys

        # string/binary fields with empty string as value
        empty_str_fields = [
            key
            for (key, val) in field_updates.items()
            if next(iter(val.keys())) in ["S", "B"] and next(iter(val.values())) == ""
        ]
        return any([keyname in empty_str_fields for keyname in key_names])
    return False


def put_has_empty_attrs(field_updates, table):
    # Example invalid attribute: [{'M': {'SS': {'NS': []}}}]
    def _validate_attr(attr: dict):
        if "NS" in attr and attr["NS"] == []:
            return True
        else:
            return any(
                [_validate_attr(val) for val in attr.values() if isinstance(val, dict)]
            )

    if table:
        key_names = table.attribute_keys
        attrs_to_check = [
            val for attr, val in field_updates.items() if attr not in key_names
        ]
        return any([_validate_attr(attr) for attr in attrs_to_check])
    return False


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
            if isinstance(response, str):
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
                raise MockValidationException(
                    "ProvisionedThroughput cannot be specified when BillingMode is PAY_PER_REQUEST"
                )
            throughput = None
            billing_mode = "PAY_PER_REQUEST"
        else:  # Provisioned (default billing mode)
            throughput = body.get("ProvisionedThroughput")
            if throughput is None:
                raise MockValidationException(
                    "One or more parameter values were invalid: ReadCapacityUnits and WriteCapacityUnits must both be specified when BillingMode is PROVISIONED"
                )
            billing_mode = "PROVISIONED"
        # getting ServerSideEncryption details
        sse_spec = body.get("SSESpecification")
        # getting the schema
        key_schema = body["KeySchema"]
        # getting attribute definition
        attr = body["AttributeDefinitions"]
        # getting the indexes
        global_indexes = body.get("GlobalSecondaryIndexes")
        if global_indexes == []:
            raise MockValidationException(
                "One or more parameter values were invalid: List of GlobalSecondaryIndexes is empty"
            )
        global_indexes = global_indexes or []
        local_secondary_indexes = body.get("LocalSecondaryIndexes")
        if local_secondary_indexes == []:
            raise MockValidationException(
                "One or more parameter values were invalid: List of LocalSecondaryIndexes is empty"
            )
        local_secondary_indexes = local_secondary_indexes or []
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
            return self._throw_attr_error(
                actual_attrs, expected_attrs, global_indexes or local_secondary_indexes
            )
        # get the stream specification
        streams = body.get("StreamSpecification")
        # Get any tags
        tags = body.get("Tags", [])

        table = self.dynamodb_backend.create_table(
            table_name,
            schema=key_schema,
            throughput=throughput,
            attr=attr,
            global_indexes=global_indexes,
            indexes=local_secondary_indexes,
            streams=streams,
            billing_mode=billing_mode,
            sse_specification=sse_spec,
            tags=tags,
        )
        return dynamo_json_dump(table.describe())

    def _throw_attr_error(self, actual_attrs, expected_attrs, indexes):
        def dump_list(list_):
            return str(list_).replace("'", "")

        err_head = "One or more parameter values were invalid: "
        if len(actual_attrs) > len(expected_attrs):
            if indexes:
                raise MockValidationException(
                    err_head
                    + "Some AttributeDefinitions are not used. AttributeDefinitions: "
                    + dump_list(actual_attrs)
                    + ", keys used: "
                    + dump_list(expected_attrs)
                )
            else:
                raise MockValidationException(
                    err_head
                    + "Number of attributes in KeySchema does not exactly match number of attributes defined in AttributeDefinitions"
                )
        elif len(actual_attrs) < len(expected_attrs):
            if indexes:
                raise MockValidationException(
                    err_head
                    + "Some index key attributes are not defined in AttributeDefinitions. Keys: "
                    + dump_list(list(set(expected_attrs) - set(actual_attrs)))
                    + ", AttributeDefinitions: "
                    + dump_list(actual_attrs)
                )
            else:
                raise MockValidationException(
                    "Invalid KeySchema: Some index key attribute have no definition"
                )
        else:
            if indexes:
                raise MockValidationException(
                    err_head
                    + "Some index key attributes are not defined in AttributeDefinitions. Keys: "
                    + dump_list(list(set(expected_attrs) - set(actual_attrs)))
                    + ", AttributeDefinitions: "
                    + dump_list(actual_attrs)
                )
            else:
                raise MockValidationException(
                    err_head
                    + "Some index key attributes are not defined in AttributeDefinitions. Keys: "
                    + dump_list(expected_attrs)
                    + ", AttributeDefinitions: "
                    + dump_list(actual_attrs)
                )

    def delete_table(self):
        name = self.body["TableName"]
        table = self.dynamodb_backend.delete_table(name)
        return dynamo_json_dump(table.describe())

    def describe_endpoints(self):
        response = {"Endpoints": self.dynamodb_backend.describe_endpoints()}
        return dynamo_json_dump(response)

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

    def update_table(self):
        name = self.body["TableName"]
        attr_definitions = self.body.get("AttributeDefinitions", None)
        global_index = self.body.get("GlobalSecondaryIndexUpdates", None)
        throughput = self.body.get("ProvisionedThroughput", None)
        billing_mode = self.body.get("BillingMode", None)
        stream_spec = self.body.get("StreamSpecification", None)
        table = self.dynamodb_backend.update_table(
            name=name,
            attr_definitions=attr_definitions,
            global_index=global_index,
            throughput=throughput,
            billing_mode=billing_mode,
            stream_spec=stream_spec,
        )
        return dynamo_json_dump(table.describe())

    def describe_table(self):
        name = self.body["TableName"]
        table = self.dynamodb_backend.describe_table(name)
        return dynamo_json_dump(table)

    @include_consumed_capacity()
    def put_item(self):
        name = self.body["TableName"]
        item = self.body["Item"]
        return_values = self.body.get("ReturnValues", "NONE")

        if return_values not in ("ALL_OLD", "NONE"):
            raise MockValidationException("Return values set to invalid value")

        if put_has_empty_keys(item, self.dynamodb_backend.get_table(name)):
            raise MockValidationException(
                "One or more parameter values were invalid: An AttributeValue may not contain an empty string"
            )
        if put_has_empty_attrs(item, self.dynamodb_backend.get_table(name)):
            raise MockValidationException(
                "One or more parameter values were invalid: An number set  may not be empty"
            )

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

        result = self.dynamodb_backend.put_item(
            name,
            item,
            expected,
            condition_expression,
            expression_attribute_names,
            expression_attribute_values,
            overwrite,
        )

        item_dict = result.to_json()
        if return_values == "ALL_OLD":
            item_dict["Attributes"] = existing_attributes
        else:
            item_dict.pop("Attributes", None)
        return dynamo_json_dump(item_dict)

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
                    self.dynamodb_backend.delete_item(table_name, keys)

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

    @include_consumed_capacity(0.5)
    def get_item(self):
        name = self.body["TableName"]
        self.dynamodb_backend.get_table(name)
        key = self.body["Key"]
        projection_expression = self.body.get("ProjectionExpression")
        expression_attribute_names = self.body.get("ExpressionAttributeNames")
        if expression_attribute_names == {}:
            if projection_expression is None:
                raise MockValidationException(
                    "ExpressionAttributeNames can only be specified when using expressions"
                )
            else:
                raise MockValidationException(
                    "ExpressionAttributeNames must not be empty"
                )

        expression_attribute_names = expression_attribute_names or {}
        projection_expression = self._adjust_projection_expression(
            projection_expression, expression_attribute_names
        )

        item = self.dynamodb_backend.get_item(name, key, projection_expression)
        if item:
            item_dict = item.describe_attrs(attributes=None)
            return dynamo_json_dump(item_dict)
        else:
            # Item not found
            return dynamo_json_dump({})

    def batch_get_item(self):
        table_batches = self.body["RequestItems"]

        results = {"ConsumedCapacity": [], "Responses": {}, "UnprocessedKeys": {}}

        # Validation: Can only request up to 100 items at the same time
        # Scenario 1: We're requesting more than a 100 keys from a single table
        for table_name, table_request in table_batches.items():
            if len(table_request["Keys"]) > 100:
                raise MockValidationException(
                    "1 validation error detected: Value at 'requestItems."
                    + table_name
                    + ".member.keys' failed to satisfy constraint: Member must have length less than or equal to 100"
                )
        # Scenario 2: We're requesting more than a 100 keys across all tables
        nr_of_keys_across_all_tables = sum(
            [len(req["Keys"]) for _, req in table_batches.items()]
        )
        if nr_of_keys_across_all_tables > 100:
            raise MockValidationException(
                "Too many items requested for the BatchGetItem call"
            )

        for table_name, table_request in table_batches.items():
            keys = table_request["Keys"]
            if self._contains_duplicates(keys):
                raise MockValidationException(
                    "Provided list of item keys contains duplicates"
                )
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

    @include_consumed_capacity()
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

            index_name = self.body.get("IndexName")
            schema = self.dynamodb_backend.get_schema(
                table_name=name, index_name=index_name
            )

            reverse_attribute_lookup = dict(
                (v, k) for k, v in self.body.get("ExpressionAttributeNames", {}).items()
            )

            if " and " in key_condition_expression.lower():
                expressions = re.split(
                    " AND ", key_condition_expression, maxsplit=1, flags=re.IGNORECASE
                )

                index_hash_key = [key for key in schema if key["KeyType"] == "HASH"][0]
                hash_key_var = reverse_attribute_lookup.get(
                    index_hash_key["AttributeName"], index_hash_key["AttributeName"]
                )
                hash_key_regex = r"(^|[\s(]){0}\b".format(hash_key_var)
                i, hash_key_expression = next(
                    (
                        (i, e)
                        for i, e in enumerate(expressions)
                        if re.search(hash_key_regex, e)
                    ),
                    (None, None),
                )
                if hash_key_expression is None:
                    raise MockValidationException(
                        "Query condition missed key schema element: {}".format(
                            hash_key_var
                        )
                    )
                hash_key_expression = hash_key_expression.strip("()")
                expressions.pop(i)

                # TODO implement more than one range expression and OR operators
                range_key_expression = expressions[0].strip("()")
                # Split expression, and account for all kinds of whitespacing around commas and brackets
                range_key_expression_components = re.split(
                    r"\s*\(\s*|\s*,\s*|\s", range_key_expression
                )
                # Skip whitespace
                range_key_expression_components = [
                    c for c in range_key_expression_components if c
                ]
                range_comparison = range_key_expression_components[1]

                if " and " in range_key_expression.lower():
                    range_comparison = "BETWEEN"
                    # [range_key, between, x, and, y]
                    range_values = [
                        value_alias_map[range_key_expression_components[2]],
                        value_alias_map[range_key_expression_components[4]],
                    ]
                    supplied_range_key = range_key_expression_components[0]
                elif "begins_with" in range_key_expression:
                    range_comparison = "BEGINS_WITH"
                    # [begins_with, range_key, x]
                    range_values = [
                        value_alias_map[range_key_expression_components[-1]]
                    ]
                    supplied_range_key = range_key_expression_components[1]
                elif "begins_with" in range_key_expression.lower():
                    function_used = range_key_expression[
                        range_key_expression.lower().index("begins_with") : len(
                            "begins_with"
                        )
                    ]
                    raise MockValidationException(
                        "Invalid KeyConditionExpression: Invalid function name; function: {}".format(
                            function_used
                        )
                    )
                else:
                    # [range_key, =, x]
                    range_values = [value_alias_map[range_key_expression_components[2]]]
                    supplied_range_key = range_key_expression_components[0]

                supplied_range_key = expression_attribute_names.get(
                    supplied_range_key, supplied_range_key
                )
                range_keys = [
                    k["AttributeName"] for k in schema if k["KeyType"] == "RANGE"
                ]
                if supplied_range_key not in range_keys:
                    raise MockValidationException(
                        "Query condition missed key schema element: {}".format(
                            range_keys[0]
                        )
                    )
            else:
                hash_key_expression = key_condition_expression.strip("()")
                range_comparison = None
                range_values = []

            if not re.search("[^<>]=", hash_key_expression):
                raise MockValidationException("Query key condition not supported")
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
                raise MockValidationException(
                    "Either KeyConditions or QueryFilter should be present"
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
                    raise ResourceNotFoundException
                hash_key = key_conditions[hash_key_name]["AttributeValueList"][0]
                if len(key_conditions) == 1:
                    range_comparison = None
                    range_values = []
                else:
                    if range_key_name is None and not filter_kwargs:
                        raise MockValidationException("Validation Exception")
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

        result = {
            "Count": len(items),
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

    @include_consumed_capacity()
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
        except ValueError as err:
            raise MockValidationException("Bad Filter Expression: {0}".format(err))

        result = {
            "Count": len(items),
            "Items": [item.attrs for item in items],
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
            raise MockValidationException("Return values set to invalid value")

        try:
            self.dynamodb_backend.get_table(name)
        except ResourceNotFoundException:
            raise ConditionalCheckFailed(
                "A condition specified in the operation could not be evaluated."
            )

        # Attempt to parse simple ConditionExpressions into an Expected
        # expression
        condition_expression = self.body.get("ConditionExpression")
        expression_attribute_names = self.body.get("ExpressionAttributeNames", {})
        expression_attribute_values = self.body.get("ExpressionAttributeValues", {})

        item = self.dynamodb_backend.delete_item(
            name,
            key,
            expression_attribute_names,
            expression_attribute_values,
            condition_expression,
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
        if update_expression and attribute_updates:
            raise MockValidationException(
                "Can not use both expression and non-expression parameters in the same request: Non-expression parameters: {AttributeUpdates} Expression parameters: {UpdateExpression}"
            )
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
            raise MockValidationException("Return values set to invalid value")

        if "Expected" in self.body:
            expected = self.body["Expected"]
        else:
            expected = None

        # Attempt to parse simple ConditionExpressions into an Expected
        # expression
        condition_expression = self.body.get("ConditionExpression")
        expression_attribute_names = self.body.get("ExpressionAttributeNames", {})
        expression_attribute_values = self.body.get("ExpressionAttributeValues", {})

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

            raise MockValidationException(msg)

        ret_consumed_capacity = self.body.get("ReturnConsumedCapacity", "NONE")
        consumed_capacity = dict()

        for transact_item in transact_items:

            table_name = transact_item["Get"]["TableName"]
            key = transact_item["Get"]["Key"]
            item = self.dynamodb_backend.get_item(table_name, key)

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
        self.dynamodb_backend.transact_write_items(transact_items)
        response = {"ConsumedCapacity": [], "ItemCollectionMetrics": {}}
        return dynamo_json_dump(response)

    def describe_continuous_backups(self):
        name = self.body["TableName"]

        response = self.dynamodb_backend.describe_continuous_backups(name)

        return json.dumps({"ContinuousBackupsDescription": response})

    def update_continuous_backups(self):
        name = self.body["TableName"]
        point_in_time_spec = self.body["PointInTimeRecoverySpecification"]

        response = self.dynamodb_backend.update_continuous_backups(
            name, point_in_time_spec
        )

        return json.dumps({"ContinuousBackupsDescription": response})

    def list_backups(self):
        body = self.body
        table_name = body.get("TableName")
        backups = self.dynamodb_backend.list_backups(table_name)
        response = {"BackupSummaries": [backup.summary for backup in backups]}
        return dynamo_json_dump(response)

    def create_backup(self):
        body = self.body
        table_name = body.get("TableName")
        backup_name = body.get("BackupName")
        backup = self.dynamodb_backend.create_backup(table_name, backup_name)
        response = {"BackupDetails": backup.details}
        return dynamo_json_dump(response)

    def delete_backup(self):
        body = self.body
        backup_arn = body.get("BackupArn")
        backup = self.dynamodb_backend.delete_backup(backup_arn)
        response = {"BackupDescription": backup.description}
        return dynamo_json_dump(response)

    def describe_backup(self):
        body = self.body
        backup_arn = body.get("BackupArn")
        backup = self.dynamodb_backend.describe_backup(backup_arn)
        response = {"BackupDescription": backup.description}
        return dynamo_json_dump(response)

    def restore_table_from_backup(self):
        body = self.body
        target_table_name = body.get("TargetTableName")
        backup_arn = body.get("BackupArn")
        restored_table = self.dynamodb_backend.restore_table_from_backup(
            target_table_name, backup_arn
        )
        return dynamo_json_dump(restored_table.describe())

    def restore_table_to_point_in_time(self):
        body = self.body
        target_table_name = body.get("TargetTableName")
        source_table_name = body.get("SourceTableName")
        restored_table = self.dynamodb_backend.restore_table_to_point_in_time(
            target_table_name, source_table_name
        )
        return dynamo_json_dump(restored_table.describe())
