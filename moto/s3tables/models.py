"""S3TablesBackend class with methods for supported APIs."""

import datetime
from base64 import b64decode, b64encode
from typing import Any, Dict, List, Optional, Tuple

from moto.core.base_backend import BackendDict, BaseBackend
from moto.s3tables.exceptions import BadRequestException
from moto.utilities.utils import get_partition

S3TABLES_DEFAULT_MAX_BUCKETS = 1000


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

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.table_buckets: Dict[str, FakeTableBucket] = {}

    def create_table_bucket(self, name: str) -> str:
        new_table_bucket = FakeTableBucket(
            name=name, account_id=self.account_id, region_name=self.region_name
        )
        self.table_buckets[new_table_bucket.arn] = new_table_bucket
        return new_table_bucket.arn

    def list_table_buckets(
        self,
        prefix: Optional[str] = None,
        continuation_token: Optional[str] = None,
        max_buckets: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        if not max_buckets:
            max_buckets = S3TABLES_DEFAULT_MAX_BUCKETS

        all_buckets = list(
            bucket
            for bucket in self.table_buckets.values()
            if (prefix is None or bucket.name.startswith(prefix))
        )

        # encode bucket arn in the continuation_token together with prefix value
        # raise invalidcontinuationtoken if the prefix changed
        if continuation_token:
            # expect continuation token to be b64encoded
            token_arn, token_prefix = (
                b64decode(continuation_token.encode()).decode("utf-8").split(" ", 1)
            )
            # TODO: validate prefix
            if token_prefix and token_prefix != prefix:
                raise BadRequestException("The continuation token is not valid")
            last_bucket_index = list(b.arn for b in all_buckets).index(token_arn)
            start = last_bucket_index + 1
        else:
            start = 0

        buckets = all_buckets[start : start + max_buckets]

        table_buckets = [
            {
                "arn": b.arn,
                "name": b.name,
                "ownerAccountId": b.account_id,
                "createdAt": b.creation_date.isoformat(),
            }
            for b in buckets
        ]
        next_continuation_token = None
        if start + max_buckets < len(all_buckets):
            next_continuation_token = b64encode(
                f"{buckets[-1].arn} {prefix if prefix else ''}".encode()
            ).decode()

        return table_buckets, next_continuation_token

    def get_table_bucket(self, table_bucket_arn: str) -> Tuple[str, str, str, str]:
        bucket = self.table_buckets.get(table_bucket_arn)
        if not bucket:
            raise KeyError
        return (
            bucket.arn,
            bucket.name,
            bucket.account_id,
            bucket.creation_date.isoformat(),
        )

    def delete_table_bucket(self, table_bucket_arn: str) -> None:
        self.table_buckets.pop(table_bucket_arn)


s3tables_backends = BackendDict(
    S3TablesBackend,
    "s3tables",
    additional_regions=["us-east-1", "us-east-2", "us-west-2"],
)
