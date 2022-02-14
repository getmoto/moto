from moto.core import ACCOUNT_ID, BaseBackend, BaseModel
from moto.core.utils import BackendDict


class TimestreamTable(BaseModel):
    def __init__(self, region_name, table_name, db_name, retention_properties):
        self.region_name = region_name
        self.name = table_name
        self.db_name = db_name
        self.retention_properties = retention_properties
        self.records = []

    def update(self, retention_properties):
        self.retention_properties = retention_properties

    def write_records(self, records):
        self.records.extend(records)

    @property
    def arn(self):
        return f"arn:aws:timestream:{self.region_name}:{ACCOUNT_ID}:database/{self.db_name}/table/{self.name}"

    def description(self):
        return {
            "Arn": self.arn,
            "TableName": self.name,
            "DatabaseName": self.db_name,
            "TableStatus": "ACTIVE",
            "RetentionProperties": self.retention_properties,
        }


class TimestreamDatabase(BaseModel):
    def __init__(self, region_name, database_name, kms_key_id):
        self.region_name = region_name
        self.name = database_name
        self.kms_key_id = kms_key_id
        self.tables = dict()

    def update(self, kms_key_id):
        self.kms_key_id = kms_key_id

    def create_table(self, table_name, retention_properties):
        table = TimestreamTable(
            region_name=self.region_name,
            table_name=table_name,
            db_name=self.name,
            retention_properties=retention_properties,
        )
        self.tables[table_name] = table
        return table

    def update_table(self, table_name, retention_properties):
        table = self.tables[table_name]
        table.update(retention_properties=retention_properties)
        return table

    def delete_table(self, table_name):
        del self.tables[table_name]

    def describe_table(self, table_name):
        return self.tables[table_name]

    def list_tables(self):
        return self.tables.values()

    @property
    def arn(self):
        return (
            f"arn:aws:timestream:{self.region_name}:{ACCOUNT_ID}:database/{self.name}"
        )

    def description(self):
        return {
            "Arn": self.arn,
            "DatabaseName": self.name,
            "TableCount": len(self.tables.keys()),
            "KmsKeyId": self.kms_key_id,
        }


class TimestreamWriteBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        self.databases = dict()

    def create_database(self, database_name, kms_key_id, tags):
        database = TimestreamDatabase(self.region_name, database_name, kms_key_id)
        self.databases[database_name] = database
        return database

    def delete_database(self, database_name):
        del self.databases[database_name]

    def describe_database(self, database_name):
        return self.databases[database_name]

    def list_databases(self):
        return self.databases.values()

    def update_database(self, database_name, kms_key_id):
        database = self.databases[database_name]
        database.update(kms_key_id=kms_key_id)
        return database

    def create_table(self, database_name, table_name, retention_properties):
        database = self.describe_database(database_name)
        table = database.create_table(table_name, retention_properties)
        return table

    def delete_table(self, database_name, table_name):
        database = self.describe_database(database_name)
        database.delete_table(table_name)

    def describe_table(self, database_name, table_name):
        database = self.describe_database(database_name)
        table = database.describe_table(table_name)
        return table

    def list_tables(self, database_name):
        database = self.describe_database(database_name)
        tables = database.list_tables()
        return tables

    def update_table(self, database_name, table_name, retention_properties):
        database = self.describe_database(database_name)
        table = database.update_table(table_name, retention_properties)
        return table

    def write_records(self, database_name, table_name, records):
        database = self.describe_database(database_name)
        table = database.describe_table(table_name)
        table.write_records(records)

    def describe_endpoints(self):
        # https://docs.aws.amazon.com/timestream/latest/developerguide/Using-API.endpoint-discovery.how-it-works.html
        # Usually, the address look like this:
        # ingest-cell1.timestream.us-east-1.amazonaws.com
        # Where 'cell1' can be any number, 'cell2', 'cell3', etc - whichever endpoint happens to be available for that particular account
        # We don't implement a cellular architecture in Moto though, so let's keep it simple
        return {
            "Endpoints": [
                {
                    "Address": f"ingest.timestream.{self.region_name}.amazonaws.com",
                    "CachePeriodInMinutes": 1440,
                }
            ]
        }

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)


timestreamwrite_backends = BackendDict(TimestreamWriteBackend, "timestream-write")

# Boto does not return any regions at the time of writing (20/10/2021)
# Hardcoding the known regions for now
# Thanks, Jeff
for r in ["us-east-1", "us-east-2", "us-west-2", "eu-central-1", "eu-west-1"]:
    timestreamwrite_backends[r] = TimestreamWriteBackend(r)
