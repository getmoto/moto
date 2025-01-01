"""S3TablesBackend class with methods for supported APIs."""

import datetime
from typing import Dict

from moto.core.base_backend import BackendDict
from moto.core.base_backend import BaseBackend
from moto.core.common_models import BaseModel
from moto.utilities.utils import get_partition


class FakeTableBucket:
    def __init__(self, name: str, account_id: str, region_name: str):
        self.name = name
        self.account_id = account_id
        self.region_name = region_name
        self.partition = get_partition(region_name)
        self.creation_date = datetime.datetime.now(tz=datetime.timezone.utc)

    @property
    def arn(self) -> str:
        return f"arn:{self.partition}:s3tables:{self.region_name}:{self.account_id}:bucket/{self.name}"

class S3TablesBackend(BaseBackend):
    """Implementation of S3Tables APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.table_buckets: Dict[str, FakeTableBucket] = {}

    def create_table_bucket(self, name) -> str:
        new_table_bucket = FakeTableBucket(
            name=name, account_id=self.account_id, region_name=self.region_name
        )
        self.table_buckets[name] = new_table_bucket
        return new_table_bucket.arn

    def list_table_buckets(self, prefix, continuation_token, max_buckets):
        # implement here
        return table_buckets, continuation_token
    
    def get_table_bucket(self, table_bucket_arn):
        # implement here
        return arn, name, owner_account_id, created_at
    
    def delete_table_bucket(self, table_bucket_arn):
        # implement here
        return 
    

s3tables_backends = BackendDict(
    S3TablesBackend,
    "s3tables",
    additional_regions=["us-east-1", "us-east-2", "us-west-2"],
)
