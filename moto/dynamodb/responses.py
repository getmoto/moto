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
        tables = dynamodb_backend.tables.keys()
        response = {"TableNames": tables}
        return json.dumps(response)

    def DescribeTable(self, uri, body, headers):
        name = json.loads(body)['TableName']
        try:
            table = dynamodb_backend.tables[name]
        except KeyError:
            er = 'com.amazonaws.dynamodb.v20111205#ResourceNotFoundException'
            return self.error(er)
        return json.dumps(table.describe)


def handler(uri, body, headers):
    return DynamoHandler(uri, body, headers_to_dict(headers)).dispatch()
