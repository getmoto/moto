from __future__ import unicode_literals
import json
import six
import re

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores, amzn_request_id
from .exceptions import InvalidIndexNameError
from .models import dynamodb_backends, dynamo_json_dump


def has_empty_keys_or_values(_dict):
    if _dict == "":
        return True
    if not isinstance(_dict, dict):
        return False
    return any(
        key == '' or value == '' or
        has_empty_keys_or_values(value)
        for key, value in _dict.items()
    )


def get_empty_str_error():
    er = 'com.amazonaws.dynamodb.v20111205#ValidationException'
    return (400,
            {'server': 'amazon.com'},
            dynamo_json_dump({'__type': er,
                              'message': ('One or more parameter values were '
                                          'invalid: An AttributeValue may not '
                                          'contain an empty string')}
                             ))


def condition_expression_to_expected(condition_expression, expression_attribute_names, expression_attribute_values):
    """
    Limited condition expression syntax parsing.
    Supports Global Negation ex: NOT(inner expressions).
    Supports simple AND conditions ex: cond_a AND cond_b and cond_c.
    Atomic expressions supported are attribute_exists(key), attribute_not_exists(key) and #key = :value.
    """
    expected = {}
    if condition_expression and 'OR' not in condition_expression:
        reverse_re = re.compile('^NOT\s*\((.*)\)$')
        reverse_m = reverse_re.match(condition_expression.strip())

        reverse = False
        if reverse_m:
            reverse = True
            condition_expression = reverse_m.group(1)

        cond_items = [c.strip() for c in condition_expression.split('AND')]
        if cond_items:
            exists_re = re.compile('^attribute_exists\s*\((.*)\)$')
            not_exists_re = re.compile(
                '^attribute_not_exists\s*\((.*)\)$')
            equals_re = re.compile('^(#?\w+)\s*=\s*(\:?\w+)')

        for cond in cond_items:
            exists_m = exists_re.match(cond)
            not_exists_m = not_exists_re.match(cond)
            equals_m = equals_re.match(cond)

            if exists_m:
                attribute_name = expression_attribute_names_lookup(exists_m.group(1), expression_attribute_names)
                expected[attribute_name] = {'Exists': True if not reverse else False}
            elif not_exists_m:
                attribute_name = expression_attribute_names_lookup(not_exists_m.group(1), expression_attribute_names)
                expected[attribute_name] = {'Exists': False if not reverse else True}
            elif equals_m:
                attribute_name = expression_attribute_names_lookup(equals_m.group(1), expression_attribute_names)
                attribute_value = expression_attribute_values_lookup(equals_m.group(2), expression_attribute_values)
                expected[attribute_name] = {
                    'AttributeValueList': [attribute_value],
                    'ComparisonOperator': 'EQ' if not reverse else 'NEQ'}

    return expected


def expression_attribute_names_lookup(attribute_name, expression_attribute_names):
    if attribute_name.startswith('#') and attribute_name in expression_attribute_names:
        return expression_attribute_names[attribute_name]
    else:
        return attribute_name


def expression_attribute_values_lookup(attribute_value, expression_attribute_values):
    if isinstance(attribute_value, six.string_types) and \
            attribute_value.startswith(':') and\
            attribute_value in expression_attribute_values:
        return expression_attribute_values[attribute_value]
    else:
        return attribute_value


class DynamoHandler(BaseResponse):

    def get_endpoint_name(self, headers):
        """Parses request headers and extracts part od the X-Amz-Target
        that corresponds to a method of DynamoHandler

        ie: X-Amz-Target: DynamoDB_20111205.ListTables -> ListTables
        """
        # Headers are case-insensitive. Probably a better way to do this.
        match = headers.get('x-amz-target') or headers.get('X-Amz-Target')
        if match:
            return match.split(".")[1]

    def error(self, type_, message, status=400):
        return status, self.response_headers, dynamo_json_dump({'__type': type_, 'message': message})

    @property
    def dynamodb_backend(self):
        """
        :return: DynamoDB2 Backend
        :rtype: moto.dynamodb2.models.DynamoDBBackend
        """
        return dynamodb_backends[self.region]

    @amzn_request_id
    def call_action(self):
        self.body = json.loads(self.body or '{}')
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
        limit = body.get('Limit', 100)
        if body.get("ExclusiveStartTableName"):
            last = body.get("ExclusiveStartTableName")
            start = list(self.dynamodb_backend.tables.keys()).index(last) + 1
        else:
            start = 0
        all_tables = list(self.dynamodb_backend.tables.keys())
        if limit:
            tables = all_tables[start:start + limit]
        else:
            tables = all_tables[start:]
        response = {"TableNames": tables}
        if limit and len(all_tables) > start + limit:
            response["LastEvaluatedTableName"] = tables[-1]

        return dynamo_json_dump(response)

    def create_table(self):
        body = self.body
        # get the table name
        table_name = body['TableName']
        # check billing mode and get the throughput
        if "BillingMode" in body.keys() and body["BillingMode"] == "PAY_PER_REQUEST":
            if "ProvisionedThroughput" in body.keys():
                er = 'com.amazonaws.dynamodb.v20111205#ValidationException'
                return self.error(er,
                                  'ProvisionedThroughput cannot be specified \
                                   when BillingMode is PAY_PER_REQUEST')
            throughput = None
        else:         # Provisioned (default billing mode)
            throughput = body.get("ProvisionedThroughput")
        # getting the schema
        key_schema = body['KeySchema']
        # getting attribute definition
        attr = body["AttributeDefinitions"]
        # getting the indexes
        global_indexes = body.get("GlobalSecondaryIndexes", [])
        local_secondary_indexes = body.get("LocalSecondaryIndexes", [])
        # get the stream specification
        streams = body.get("StreamSpecification")

        table = self.dynamodb_backend.create_table(table_name,
                                                   schema=key_schema,
                                                   throughput=throughput,
                                                   attr=attr,
                                                   global_indexes=global_indexes,
                                                   indexes=local_secondary_indexes,
                                                   streams=streams)
        if table is not None:
            return dynamo_json_dump(table.describe())
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceInUseException'
            return self.error(er, 'Resource in use')

    def delete_table(self):
        name = self.body['TableName']
        table = self.dynamodb_backend.delete_table(name)
        if table is not None:
            return dynamo_json_dump(table.describe())
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er, 'Requested resource not found')

    def tag_resource(self):
        table_arn = self.body['ResourceArn']
        tags = self.body['Tags']
        self.dynamodb_backend.tag_resource(table_arn, tags)
        return ''

    def untag_resource(self):
        table_arn = self.body['ResourceArn']
        tags = self.body['TagKeys']
        self.dynamodb_backend.untag_resource(table_arn, tags)
        return ''

    def list_tags_of_resource(self):
        try:
            table_arn = self.body['ResourceArn']
            all_tags = self.dynamodb_backend.list_tags_of_resource(table_arn)
            all_tag_keys = [tag['Key'] for tag in all_tags]
            marker = self.body.get('NextToken')
            if marker:
                start = all_tag_keys.index(marker) + 1
            else:
                start = 0
            max_items = 10  # there is no default, but using 10 to make testing easier
            tags_resp = all_tags[start:start + max_items]
            next_marker = None
            if len(all_tags) > start + max_items:
                next_marker = tags_resp[-1]['Key']
            if next_marker:
                return json.dumps({'Tags': tags_resp,
                                   'NextToken': next_marker})
            return json.dumps({'Tags': tags_resp})
        except AttributeError:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er, 'Requested resource not found')

    def update_table(self):
        name = self.body['TableName']
        table = self.dynamodb_backend.get_table(name)
        if 'GlobalSecondaryIndexUpdates' in self.body:
            table = self.dynamodb_backend.update_table_global_indexes(
                name, self.body['GlobalSecondaryIndexUpdates'])
        if 'ProvisionedThroughput' in self.body:
            throughput = self.body["ProvisionedThroughput"]
            table = self.dynamodb_backend.update_table_throughput(name, throughput)
        if 'StreamSpecification' in self.body:
            try:
                table = self.dynamodb_backend.update_table_streams(name, self.body['StreamSpecification'])
            except ValueError:
                er = 'com.amazonaws.dynamodb.v20111205#ResourceInUseException'
                return self.error(er, 'Cannot enable stream')

        return dynamo_json_dump(table.describe())

    def describe_table(self):
        name = self.body['TableName']
        try:
            table = self.dynamodb_backend.tables[name]
        except KeyError:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er, 'Requested resource not found')
        return dynamo_json_dump(table.describe(base_key='Table'))

    def put_item(self):
        name = self.body['TableName']
        item = self.body['Item']
        return_values = self.body.get('ReturnValues', 'NONE')

        if return_values not in ('ALL_OLD', 'NONE'):
            er = 'com.amazonaws.dynamodb.v20111205#ValidationException'
            return self.error(er, 'Return values set to invalid value')

        if has_empty_keys_or_values(item):
            return get_empty_str_error()

        overwrite = 'Expected' not in self.body
        if not overwrite:
            expected = self.body['Expected']
        else:
            expected = None

        if return_values == 'ALL_OLD':
            existing_item = self.dynamodb_backend.get_item(name, item)
            if existing_item:
                existing_attributes = existing_item.to_json()['Attributes']
            else:
                existing_attributes = {}

        # Attempt to parse simple ConditionExpressions into an Expected
        # expression
        if not expected:
            condition_expression = self.body.get('ConditionExpression')
            expression_attribute_names = self.body.get('ExpressionAttributeNames', {})
            expression_attribute_values = self.body.get('ExpressionAttributeValues', {})
            expected = condition_expression_to_expected(condition_expression,
                                                        expression_attribute_names,
                                                        expression_attribute_values)
            if expected:
                overwrite = False

        try:
            result = self.dynamodb_backend.put_item(name, item, expected, overwrite)
        except ValueError:
            er = 'com.amazonaws.dynamodb.v20111205#ConditionalCheckFailedException'
            return self.error(er, 'A condition specified in the operation could not be evaluated.')

        if result:
            item_dict = result.to_json()
            item_dict['ConsumedCapacity'] = {
                'TableName': name,
                'CapacityUnits': 1
            }
            if return_values == 'ALL_OLD':
                item_dict['Attributes'] = existing_attributes
            else:
                item_dict.pop('Attributes', None)
            return dynamo_json_dump(item_dict)
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er, 'Requested resource not found')

    def batch_write_item(self):
        table_batches = self.body['RequestItems']

        for table_name, table_requests in table_batches.items():
            for table_request in table_requests:
                request_type = list(table_request.keys())[0]
                request = list(table_request.values())[0]
                if request_type == 'PutRequest':
                    item = request['Item']
                    self.dynamodb_backend.put_item(table_name, item)
                elif request_type == 'DeleteRequest':
                    keys = request['Key']
                    item = self.dynamodb_backend.delete_item(table_name, keys)

        response = {
            "ConsumedCapacity": [
                {
                    'TableName': table_name,
                    'CapacityUnits': 1.0,
                    'Table': {'CapacityUnits': 1.0}
                } for table_name, table_requests in table_batches.items()
            ],
            "ItemCollectionMetrics": {},
            "UnprocessedItems": {}
        }

        return dynamo_json_dump(response)

    def get_item(self):
        name = self.body['TableName']
        key = self.body['Key']
        try:
            item = self.dynamodb_backend.get_item(name, key)
        except ValueError:
            er = 'com.amazon.coral.validate#ValidationException'
            return self.error(er, 'Validation Exception')
        if item:
            item_dict = item.describe_attrs(attributes=None)
            item_dict['ConsumedCapacity'] = {
                'TableName': name,
                'CapacityUnits': 0.5
            }
            return dynamo_json_dump(item_dict)
        else:
            # Item not found
            return 200, self.response_headers, '{}'

    def batch_get_item(self):
        table_batches = self.body['RequestItems']

        results = {
            "ConsumedCapacity": [],
            "Responses": {
            },
            "UnprocessedKeys": {
            }
        }

        for table_name, table_request in table_batches.items():
            keys = table_request['Keys']
            attributes_to_get = table_request.get('AttributesToGet')
            results["Responses"][table_name] = []
            for key in keys:
                item = self.dynamodb_backend.get_item(table_name, key)
                if item:
                    item_describe = item.describe_attrs(attributes_to_get)
                    results["Responses"][table_name].append(
                        item_describe["Item"])

            results["ConsumedCapacity"].append({
                "CapacityUnits": len(keys),
                "TableName": table_name
            })
        return dynamo_json_dump(results)

    def query(self):
        name = self.body['TableName']
        # {u'KeyConditionExpression': u'#n0 = :v0', u'ExpressionAttributeValues': {u':v0': {u'S': u'johndoe'}}, u'ExpressionAttributeNames': {u'#n0': u'username'}}
        key_condition_expression = self.body.get('KeyConditionExpression')
        projection_expression = self.body.get('ProjectionExpression')
        expression_attribute_names = self.body.get('ExpressionAttributeNames', {})
        filter_expression = self.body.get('FilterExpression')
        expression_attribute_values = self.body.get('ExpressionAttributeValues', {})

        if projection_expression and expression_attribute_names:
            expressions = [x.strip() for x in projection_expression.split(',')]
            for expression in expressions:
                if expression in expression_attribute_names:
                    projection_expression = projection_expression.replace(expression, expression_attribute_names[expression])

        filter_kwargs = {}

        if key_condition_expression:
            value_alias_map = self.body.get('ExpressionAttributeValues', {})

            table = self.dynamodb_backend.get_table(name)

            # If table does not exist
            if table is None:
                return self.error('com.amazonaws.dynamodb.v20120810#ResourceNotFoundException',
                                  'Requested resource not found')

            index_name = self.body.get('IndexName')
            if index_name:
                all_indexes = (table.global_indexes or []) + \
                    (table.indexes or [])
                indexes_by_name = dict((i['IndexName'], i)
                                       for i in all_indexes)
                if index_name not in indexes_by_name:
                    raise ValueError('Invalid index: %s for table: %s. Available indexes are: %s' % (
                        index_name, name, ', '.join(indexes_by_name.keys())
                    ))

                index = indexes_by_name[index_name]['KeySchema']
            else:
                index = table.schema

            reverse_attribute_lookup = dict((v, k) for k, v in
                                            six.iteritems(self.body.get('ExpressionAttributeNames', {})))

            if " AND " in key_condition_expression:
                expressions = key_condition_expression.split(" AND ", 1)

                index_hash_key = [key for key in index if key['KeyType'] == 'HASH'][0]
                hash_key_var = reverse_attribute_lookup.get(index_hash_key['AttributeName'],
                                                            index_hash_key['AttributeName'])
                hash_key_regex = r'(^|[\s(]){0}\b'.format(hash_key_var)
                i, hash_key_expression = next((i, e) for i, e in enumerate(expressions)
                                              if re.search(hash_key_regex, e))
                hash_key_expression = hash_key_expression.strip('()')
                expressions.pop(i)

                # TODO implement more than one range expression and OR operators
                range_key_expression = expressions[0].strip('()')
                range_key_expression_components = range_key_expression.split()
                range_comparison = range_key_expression_components[1]

                if 'AND' in range_key_expression:
                    range_comparison = 'BETWEEN'
                    range_values = [
                        value_alias_map[range_key_expression_components[2]],
                        value_alias_map[range_key_expression_components[4]],
                    ]
                elif 'begins_with' in range_key_expression:
                    range_comparison = 'BEGINS_WITH'
                    range_values = [
                        value_alias_map[range_key_expression_components[1]],
                    ]
                else:
                    range_values = [value_alias_map[
                        range_key_expression_components[2]]]
            else:
                hash_key_expression = key_condition_expression.strip('()')
                range_comparison = None
                range_values = []

            hash_key_value_alias = hash_key_expression.split("=")[1].strip()
            # Temporary fix until we get proper KeyConditionExpression function
            hash_key = value_alias_map.get(hash_key_value_alias, {'S': hash_key_value_alias})
        else:
            # 'KeyConditions': {u'forum_name': {u'ComparisonOperator': u'EQ', u'AttributeValueList': [{u'S': u'the-key'}]}}
            key_conditions = self.body.get('KeyConditions')
            query_filters = self.body.get("QueryFilter")
            if key_conditions:
                hash_key_name, range_key_name = self.dynamodb_backend.get_table_keys_name(
                    name, key_conditions.keys())
                for key, value in key_conditions.items():
                    if key not in (hash_key_name, range_key_name):
                        filter_kwargs[key] = value
                if hash_key_name is None:
                    er = "'com.amazonaws.dynamodb.v20120810#ResourceNotFoundException"
                    return self.error(er, 'Requested resource not found')
                hash_key = key_conditions[hash_key_name][
                    'AttributeValueList'][0]
                if len(key_conditions) == 1:
                    range_comparison = None
                    range_values = []
                else:
                    if range_key_name is None and not filter_kwargs:
                        er = "com.amazon.coral.validate#ValidationException"
                        return self.error(er, 'Validation Exception')
                    else:
                        range_condition = key_conditions.get(range_key_name)
                        if range_condition:
                            range_comparison = range_condition[
                                'ComparisonOperator']
                            range_values = range_condition[
                                'AttributeValueList']
                        else:
                            range_comparison = None
                            range_values = []
            if query_filters:
                filter_kwargs.update(query_filters)
        index_name = self.body.get('IndexName')
        exclusive_start_key = self.body.get('ExclusiveStartKey')
        limit = self.body.get("Limit")
        scan_index_forward = self.body.get("ScanIndexForward")
        items, scanned_count, last_evaluated_key = self.dynamodb_backend.query(
            name, hash_key, range_comparison, range_values, limit,
            exclusive_start_key, scan_index_forward, projection_expression, index_name=index_name,
            expr_names=expression_attribute_names, expr_values=expression_attribute_values,
            filter_expression=filter_expression, **filter_kwargs
        )
        if items is None:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er, 'Requested resource not found')

        result = {
            "Count": len(items),
            'ConsumedCapacity': {
                'TableName': name,
                'CapacityUnits': 1,
            },
            "ScannedCount": scanned_count
        }

        if self.body.get('Select', '').upper() != 'COUNT':
            result["Items"] = [item.attrs for item in items]

        if last_evaluated_key is not None:
            result["LastEvaluatedKey"] = last_evaluated_key

        return dynamo_json_dump(result)

    def scan(self):
        name = self.body['TableName']

        filters = {}
        scan_filters = self.body.get('ScanFilter', {})
        for attribute_name, scan_filter in scan_filters.items():
            # Keys are attribute names. Values are tuples of (comparison,
            # comparison_value)
            comparison_operator = scan_filter["ComparisonOperator"]
            comparison_values = scan_filter.get("AttributeValueList", [])
            filters[attribute_name] = (comparison_operator, comparison_values)

        filter_expression = self.body.get('FilterExpression')
        expression_attribute_values = self.body.get('ExpressionAttributeValues', {})
        expression_attribute_names = self.body.get('ExpressionAttributeNames', {})
        projection_expression = self.body.get('ProjectionExpression', '')
        exclusive_start_key = self.body.get('ExclusiveStartKey')
        limit = self.body.get("Limit")
        index_name = self.body.get('IndexName')

        try:
            items, scanned_count, last_evaluated_key = self.dynamodb_backend.scan(name, filters,
                                                                                  limit,
                                                                                  exclusive_start_key,
                                                                                  filter_expression,
                                                                                  expression_attribute_names,
                                                                                  expression_attribute_values,
                                                                                  index_name,
                                                                                  projection_expression)
        except InvalidIndexNameError as err:
            er = 'com.amazonaws.dynamodb.v20111205#ValidationException'
            return self.error(er, str(err))
        except ValueError as err:
            er = 'com.amazonaws.dynamodb.v20111205#ValidationError'
            return self.error(er, 'Bad Filter Expression: {0}'.format(err))
        except Exception as err:
            er = 'com.amazonaws.dynamodb.v20111205#InternalFailure'
            return self.error(er, 'Internal error. {0}'.format(err))

        # Items should be a list, at least an empty one. Is None if table does not exist.
        # Should really check this at the beginning
        if items is None:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er, 'Requested resource not found')

        result = {
            "Count": len(items),
            "Items": [item.attrs for item in items],
            'ConsumedCapacity': {
                'TableName': name,
                'CapacityUnits': 1,
            },
            "ScannedCount": scanned_count
        }
        if last_evaluated_key is not None:
            result["LastEvaluatedKey"] = last_evaluated_key
        return dynamo_json_dump(result)

    def delete_item(self):
        name = self.body['TableName']
        keys = self.body['Key']
        return_values = self.body.get('ReturnValues', 'NONE')
        if return_values not in ('ALL_OLD', 'NONE'):
            er = 'com.amazonaws.dynamodb.v20111205#ValidationException'
            return self.error(er, 'Return values set to invalid value')

        table = self.dynamodb_backend.get_table(name)
        if not table:
            er = 'com.amazonaws.dynamodb.v20120810#ConditionalCheckFailedException'
            return self.error(er, 'A condition specified in the operation could not be evaluated.')

        item = self.dynamodb_backend.delete_item(name, keys)
        if item and return_values == 'ALL_OLD':
            item_dict = item.to_json()
        else:
            item_dict = {'Attributes': {}}
        item_dict['ConsumedCapacityUnits'] = 0.5
        return dynamo_json_dump(item_dict)

    def update_item(self):
        name = self.body['TableName']
        key = self.body['Key']
        return_values = self.body.get('ReturnValues', 'NONE')
        update_expression = self.body.get('UpdateExpression')
        attribute_updates = self.body.get('AttributeUpdates')
        expression_attribute_names = self.body.get(
            'ExpressionAttributeNames', {})
        expression_attribute_values = self.body.get(
            'ExpressionAttributeValues', {})
        existing_item = self.dynamodb_backend.get_item(name, key)
        if existing_item:
            existing_attributes = existing_item.to_json()['Attributes']
        else:
            existing_attributes = {}

        if return_values not in ('NONE', 'ALL_OLD', 'ALL_NEW', 'UPDATED_OLD',
                                 'UPDATED_NEW'):
            er = 'com.amazonaws.dynamodb.v20111205#ValidationException'
            return self.error(er, 'Return values set to invalid value')

        if has_empty_keys_or_values(expression_attribute_values):
            return get_empty_str_error()

        if 'Expected' in self.body:
            expected = self.body['Expected']
        else:
            expected = None

        # Attempt to parse simple ConditionExpressions into an Expected
        # expression
        if not expected:
            condition_expression = self.body.get('ConditionExpression')
            expression_attribute_names = self.body.get('ExpressionAttributeNames', {})
            expression_attribute_values = self.body.get('ExpressionAttributeValues', {})
            expected = condition_expression_to_expected(condition_expression,
                                                        expression_attribute_names,
                                                        expression_attribute_values)

        # Support spaces between operators in an update expression
        # E.g. `a = b + c` -> `a=b+c`
        if update_expression:
            update_expression = re.sub(
                '\s*([=\+-])\s*', '\\1', update_expression)

        try:
            item = self.dynamodb_backend.update_item(
                name, key, update_expression, attribute_updates, expression_attribute_names,
                expression_attribute_values, expected
            )
        except ValueError:
            er = 'com.amazonaws.dynamodb.v20111205#ConditionalCheckFailedException'
            return self.error(er, 'A condition specified in the operation could not be evaluated.')
        except TypeError:
            er = 'com.amazonaws.dynamodb.v20111205#ValidationException'
            return self.error(er, 'Validation Exception')

        item_dict = item.to_json()
        item_dict['ConsumedCapacity'] = {
            'TableName': name,
            'CapacityUnits': 0.5
        }
        unchanged_attributes = {
            k for k in existing_attributes.keys()
            if existing_attributes[k] == item_dict['Attributes'].get(k)
        }
        changed_attributes = set(existing_attributes.keys()).union(item_dict['Attributes'].keys()).difference(unchanged_attributes)

        if return_values == 'NONE':
            item_dict['Attributes'] = {}
        elif return_values == 'ALL_OLD':
            item_dict['Attributes'] = existing_attributes
        elif return_values == 'UPDATED_OLD':
            item_dict['Attributes'] = {
                k: v for k, v in existing_attributes.items()
                if k in changed_attributes
            }
        elif return_values == 'UPDATED_NEW':
            item_dict['Attributes'] = {
                k: v for k, v in item_dict['Attributes'].items()
                if k in changed_attributes
            }

        return dynamo_json_dump(item_dict)

    def describe_limits(self):
        return json.dumps({
            'AccountMaxReadCapacityUnits': 20000,
            'TableMaxWriteCapacityUnits': 10000,
            'AccountMaxWriteCapacityUnits': 20000,
            'TableMaxReadCapacityUnits': 10000
        })

    def update_time_to_live(self):
        name = self.body['TableName']
        ttl_spec = self.body['TimeToLiveSpecification']

        self.dynamodb_backend.update_ttl(name, ttl_spec)

        return json.dumps({'TimeToLiveSpecification': ttl_spec})

    def describe_time_to_live(self):
        name = self.body['TableName']

        ttl_spec = self.dynamodb_backend.describe_ttl(name)

        return json.dumps({'TimeToLiveDescription': ttl_spec})
