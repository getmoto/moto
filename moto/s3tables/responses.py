"""Handles incoming s3tables requests, invokes methods, returns responses."""

import json
from typing import Any, Dict
from urllib.parse import unquote

from moto.core.common_types import TYPE_RESPONSE
from moto.core.responses import BaseResponse

from .models import S3TablesBackend, s3tables_backends


class S3TablesResponse(BaseResponse):
    """Handler for S3Tables requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="s3tables")
        self.default_response_headers = {"Content-Type": "application/json"}

    @property
    def s3tables_backend(self) -> S3TablesBackend:
        """Return backend instance specific for this region."""
        # TODO
        # s3tables_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return s3tables_backends[self.current_account][self.region]

    # add methods from here

    def create_table_bucket(self) -> TYPE_RESPONSE:
        name = json.loads(self.body)["name"]
        bucket = self.s3tables_backend.create_table_bucket(
            name=name,
        )
        return 200, self.default_response_headers, json.dumps(dict(arn=bucket.arn))

    def list_table_buckets(self) -> TYPE_RESPONSE:
        params = self._get_params()
        prefix = params.get("prefix")
        continuation_token = params.get("continuationToken")
        max_buckets = params.get("maxBuckets")
        table_buckets, continuation_token = self.s3tables_backend.list_table_buckets(
            prefix=prefix,
            continuation_token=continuation_token,
            max_buckets=int(max_buckets) if max_buckets else None,
        )

        body: Dict[str, Any] = {
            "tableBuckets": [
                {
                    "arn": b.arn,
                    "name": b.name,
                    "ownerAccountId": b.account_id,
                    "createdAt": b.creation_date.isoformat(),
                }
                for b in table_buckets
            ]
        }
        if continuation_token:
            body.update(continuationToken=continuation_token)

        return 200, self.default_response_headers, json.dumps(body)

    def get_table_bucket(self) -> TYPE_RESPONSE:
        table_bucket_arn = unquote(self.path.split("/")[-1])
        bucket = self.s3tables_backend.get_table_bucket(
            table_bucket_arn=table_bucket_arn,
        )

        return 200, self.default_response_headers, json.dumps(
            dict(
                arn=bucket.arn,
                name=bucket.name,
                ownerAccountId=bucket.account_id,
                createdAt=bucket.creation_date.isoformat(),
            )
        )

    def delete_table_bucket(self) -> TYPE_RESPONSE:
        table_bucket_arn = unquote(self.path.split("/")[-1])
        self.s3tables_backend.delete_table_bucket(
            table_bucket_arn=table_bucket_arn,
        )

        return 204, {}, ""
