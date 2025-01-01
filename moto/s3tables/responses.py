"""Handles incoming s3tables requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import s3tables_backends


class S3TablesResponse(BaseResponse):
    """Handler for S3Tables requests and responses."""

    def __init__(self):
        super().__init__(service_name="s3tables")

    @property
    def s3tables_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # s3tables_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return s3tables_backends[self.current_account][self.region]

    # add methods from here

    
    def create_table_bucket(self):
        params = self._get_params()
        name = params.get("name")
        arn = self.s3tables_backend.create_table_bucket(
            name=name,
        )
        return json.dumps(dict(arn=arn))

    
    def list_table_buckets(self):
        params = self._get_params()
        prefix = params.get("prefix")
        continuation_token = params.get("continuationToken")
        max_buckets = params.get("maxBuckets")
        table_buckets, continuation_token = self.s3tables_backend.list_table_buckets(
            prefix=prefix,
            continuation_token=continuation_token,
            max_buckets=max_buckets,
        )
        # TODO: adjust response
        return json.dumps(dict(tableBuckets=table_buckets, continuationToken=continuation_token))
# add templates from here
    
    def get_table_bucket(self):
        params = self._get_params()
        table_bucket_arn = params.get("tableBucketARN")
        arn, name, owner_account_id, created_at = self.s3tables_backend.get_table_bucket(
            table_bucket_arn=table_bucket_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(arn=arn, name=name, ownerAccountId=owner_account_id, createdAt=created_at))
    
    def delete_table_bucket(self):
        params = self._get_params()
        table_bucket_arn = params.get("tableBucketARN")
        self.s3tables_backend.delete_table_bucket(
            table_bucket_arn=table_bucket_arn,
        )
        # TODO: adjust response
        return json.dumps(dict())
