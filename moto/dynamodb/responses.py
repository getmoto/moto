import json

from moto.core.utils import headers_to_dict
from .models import dynamodb_backend


class DynamoHandler(object):

    def __init__(self, uri, body, headers):
        self.uri = uri
        self.body = body
        self.headers = headers

    def get_method_name(self, headers):
        """Parses request headers and extracts part od the X-Amz-Target
        that corresponds to a method of DynamoHandler

        ie: X-Amz-Target: DynamoDB_20111205.ListTables -> ListTables
        """
        match = headers.get('X-Amz-Target')
        if match:
            return match.split(".")[1]

    def error(self, type_, status=400):
        return json.dumps({'__type': type_}), dict(status=400)

    def dispatch(self):
        method = self.get_method_name(self.headers)
        if method:
            return getattr(self, method)(self.uri, self.body, self.headers)
        else:
            return "", dict(status=404)

    def ListTables(self, uri, body, headers):
        limit = body.get('Limit')
        if body.get("ExclusiveStartTableName"):
            last = body.get("ExclusiveStartTableName")
            start = dynamodb_backend.tables.keys().index(last) + 1
        else:
            start = 0
        all_tables = dynamodb_backend.tables.keys()
        if limit:
            tables = all_tables[start:start + limit]
        else:
            tables = all_tables[start:]
        response = {"TableNames": tables}
        if limit and len(all_tables) > start + limit:
            response["LastEvaluatedTableName"] = tables[-1]
        return json.dumps(response)

    def CreateTable(self, uri, body, headers):
        name = body['TableName']

        key_schema = body['KeySchema']
        hash_hey = key_schema['HashKeyElement']
        hash_key_attr = hash_hey['AttributeName']
        hash_key_type = hash_hey['AttributeType']

        range_hey = key_schema['RangeKeyElement']
        range_key_attr = range_hey['AttributeName']
        range_key_type = range_hey['AttributeType']

        throughput = body["ProvisionedThroughput"]
        read_units = throughput["ReadCapacityUnits"]
        write_units = throughput["WriteCapacityUnits"]

        table = dynamodb_backend.create_table(
            name,
            hash_key_attr=hash_key_attr,
            hash_key_type=hash_key_type,
            range_key_attr=range_key_attr,
            range_key_type=range_key_type,
            read_capacity=int(read_units),
            write_capacity=int(write_units),
        )
        return json.dumps(table.describe)

    def DeleteTable(self, uri, body, headers):
        name = body['TableName']
        table = dynamodb_backend.delete_table(name)
        if table:
            return json.dumps(table.describe)
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)

    def UpdateTable(self, uri, body, headers):
        name = body['TableName']
        throughput = body["ProvisionedThroughput"]
        new_read_units = throughput["ReadCapacityUnits"]
        new_write_units = throughput["WriteCapacityUnits"]
        table = dynamodb_backend.update_table_throughput(name, new_read_units, new_write_units)
        return json.dumps(table.describe)

    def DescribeTable(self, uri, body, headers):
        name = body['TableName']
        try:
            table = dynamodb_backend.tables[name]
        except KeyError:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)
        return json.dumps(table.describe)

    def PutItem(self, uri, body, headers):
        name = body['TableName']
        item = body['Item']
        result = dynamodb_backend.put_item(name, item)
        item_dict = result.describe
        item_dict['ConsumedCapacityUnits'] = 1
        return json.dumps(item_dict)

    def GetItem(self, uri, body, headers):
        name = body['TableName']
        hash_key = body['Key']['HashKeyElement'].values()[0]
        range_key = body['Key']['RangeKeyElement'].values()[0]
        attrs_to_get = body.get('AttributesToGet')
        item = dynamodb_backend.get_item(name, hash_key, range_key)
        if item:
            item_dict = item.describe_attrs(attrs_to_get)
            item_dict['ConsumedCapacityUnits'] = 0.5
            return json.dumps(item_dict)
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)

    def Query(self, uri, body, headers):
        name = body['TableName']
        hash_key = body['HashKeyValue'].values()[0]
        range_condition = body['RangeKeyCondition']
        range_comparison = range_condition['ComparisonOperator']
        range_value = range_condition['AttributeValueList'][0].values()[0]
        items, last_page = dynamodb_backend.query(name, hash_key, range_comparison, range_value)

        result = {
            "Count": len(items),
            "Items": [item.attrs for item in items],
            "ConsumedCapacityUnits": 1,
        }

        if not last_page:
            result["LastEvaluatedKey"] = {
                "HashKeyElement": items[-1].hash_key,
                "RangeKeyElement": items[-1].range_key,
            }
        return json.dumps(result)

    def Scan(self, uri, body, headers):
        name = body['TableName']

        filters = {}
        scan_filters = body['ScanFilter']
        for attribute_name, scan_filter in scan_filters.iteritems():
            # Keys are attribute names. Values are tuples of (comparison, comparison_value)
            comparison_operator = scan_filter["ComparisonOperator"]
            comparison_value = scan_filter["AttributeValueList"][0].values()[0]
            filters[attribute_name] = (comparison_operator, comparison_value)

        items, scanned_count, last_page = dynamodb_backend.scan(name, filters)

        result = {
            "Count": len(items),
            "Items": [item.attrs for item in items],
            "ConsumedCapacityUnits": 1,
            "ScannedCount": scanned_count
        }

        if not last_page:
            result["LastEvaluatedKey"] = {
                "HashKeyElement": items[-1].hash_key,
                "RangeKeyElement": items[-1].range_key,
            }
        return json.dumps(result)

    def DeleteItem(self, uri, body, headers):
        name = body['TableName']
        hash_key = body['Key']['HashKeyElement'].values()[0]
        range_key = body['Key']['RangeKeyElement'].values()[0]
        return_values = body.get('ReturnValues', '')
        item = dynamodb_backend.delete_item(name, hash_key, range_key)
        if item:
            if return_values == 'ALL_OLD':
                item_dict = item.describe
            else:
                item_dict = {'Attributes': []}
            item_dict['ConsumedCapacityUnits'] = 0.5
            return json.dumps(item_dict)
        else:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)


def handler(uri, body, headers):
    body = json.loads(body or '{}')
    return DynamoHandler(uri, body, headers_to_dict(headers)).dispatch()
