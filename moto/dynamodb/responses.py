import re
import json
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
        match = re.search(r'X-Amz-Target: \w+\.(\w+)', headers)
        return match.groups()[0]

    def dispatch(self):
        method = self.get_method_name(self.headers)
        return getattr(self, method)(self.uri, self.body, self.headers)

    def ListTables(self, uri, body, headers):
        tables = dynamodb_backend.tables.keys()
        response = {"TableNames": tables}
        return json.dumps(response)
    

def handler(uri, body, headers):
    return DynamoHandler(uri, body, headers).dispatch()