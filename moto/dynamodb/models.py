from moto.core import BaseBackend


class DynamoDBBackend(BaseBackend):

    def __init__(self):
        self.tables = {}

    def create_table(self, name):
        self.tables[name] = None

dynamodb_backend = DynamoDBBackend()
