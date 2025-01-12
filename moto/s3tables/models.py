"""S3TablesBackend class with methods for supported APIs."""

import datetime
import re
from base64 import b64decode, b64encode
from hashlib import md5
from typing import Dict, List, Literal, Optional, Tuple, Union
from uuid import uuid4

from moto.core.base_backend import BackendDict, BaseBackend
from moto.s3tables.exceptions import (
    ConflictException,
    InvalidContinuationToken,
    InvalidNamespaceName,
    InvalidTableBucketName,
    InvalidTableName,
    NotFoundException,
)
from moto.utilities.utils import get_partition

# https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-buckets-naming.html
TABLE_BUCKET_NAME_PATTERN = re.compile(r"[a-z0-9_-]{3,63}")
TABLE_BUCKET_NAME_RESERVED_PREFIXES = ("xn--", "sthree-", "amzn-s3-demo")
TABLE_BUCKET_NAME_RESERVED_SUFFIXES = ("-s3alias", "--ol-s3", "--x-s3")
NAMESPACE_NAME_PATTERN = re.compile(r"[0-9a-z_]*")
TABLE_NAME_PATTERN = re.compile(r"[0-9a-z_]*")


def _validate_table_bucket_name(name: str) -> None:
    if (
        not TABLE_BUCKET_NAME_PATTERN.match(name)
        or any(
            name.startswith(prefix) for prefix in TABLE_BUCKET_NAME_RESERVED_PREFIXES
        )
        or any(name.endswith(suffix) for suffix in TABLE_BUCKET_NAME_RESERVED_SUFFIXES)
    ):
        raise InvalidTableBucketName()


def _validate_namespace_name(name: str) -> None:
    if not NAMESPACE_NAME_PATTERN.match(name):
        raise InvalidNamespaceName()


def _validate_table_name(name: str) -> None:
    if not TABLE_NAME_PATTERN.match(name):
        raise InvalidTableName(name)


S3TABLES_DEFAULT_MAX_BUCKETS = 1000
S3TABLES_DEFAULT_MAX_NAMESPACES = 1000
S3TABLES_DEFAULT_MAX_TABLES = 1000


class Table:
    def __init__(
        self,
        name: str,
        account_id: str,
        created_by: str,
        format: Literal["ICEBERG"],
        namespace: str,
        table_bucket_arn: str,
        type: Union[Literal["customer"], Literal["aws"]],
        managed_by_service: bool,
    ):
        _validate_table_name(name)
        self.name = name
        self.account_id = account_id
        self.created_by = created_by
        self.format = format
        self.version_token = self._generate_version_token()
        self.creation_date = datetime.datetime.now(tz=datetime.timezone.utc)
        self.last_modified = self.creation_date
        self.modified_by: Optional[str] = None
        self.namespace = namespace
        self.table_bucket_arn = table_bucket_arn
        self.managed_by_service = managed_by_service
        self.metadata_location: Optional[str] = None
        self._s3_bucket_name = self._generate_s3_bucket_name()
        self.warehouse_location: str = f"s3://{self._s3_bucket_name}"

    @property
    def arn(self) -> str:
        return f"{self.table_bucket_arn}/table/{self.name}"

    def _generate_version_token(self) -> str:
        return md5(uuid4().bytes).hexdigest()[:20]

    def _generate_s3_bucket_name(self) -> str:
        # every s3 table is assigned a unique s3 bucket with a random name
        hash = md5(self.table_bucket_arn.encode())
        hash.update(self.namespace.encode())
        hash.update(self.name.encode())
        return f"{str(uuid4())[:21]}{hash.hexdigest()[:34]}--table-s3"


class Namespace:
    def __init__(self, name: str, account_id: str, created_by: str):
        _validate_namespace_name(name)
        self.name = name
        self.account_id = account_id
        self.created_by = created_by
        self.creation_date = datetime.datetime.now(tz=datetime.timezone.utc)
        self.tables: dict[str, Table] = {}


class FakeTableBucket:
    def __init__(self, name: str, account_id: str, region_name: str):
        self.name = name
        self.account_id = account_id
        self.region_name = region_name
        self.partition = get_partition(region_name)
        self.creation_date = datetime.datetime.now(tz=datetime.timezone.utc)
        self.namespaces: dict[str, Namespace] = {}

    @property
    def arn(self) -> str:
        return f"arn:{self.partition}:s3tables:{self.region_name}:{self.account_id}:bucket/{self.name}"


class S3TablesBackend(BaseBackend):
    """Implementation of S3Tables APIs."""

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.table_buckets: Dict[str, FakeTableBucket] = {}

    def create_table_bucket(self, name: str) -> FakeTableBucket:
        _validate_table_bucket_name(name)
        new_table_bucket = FakeTableBucket(
            name=name, account_id=self.account_id, region_name=self.region_name
        )
        if new_table_bucket.arn in self.table_buckets:
            raise ConflictException(
                "The bucket that you tried to create already exists, and you own it."
            )
        self.table_buckets[new_table_bucket.arn] = new_table_bucket

        return new_table_bucket

    def list_table_buckets(
        self,
        prefix: Optional[str] = None,
        continuation_token: Optional[str] = None,
        max_buckets: Optional[int] = None,
    ) -> Tuple[List[FakeTableBucket], Optional[str]]:
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
                b64decode(continuation_token.encode()).decode("utf-8").split("|")
            )
            if token_prefix and token_prefix != prefix:
                raise InvalidContinuationToken()
            last_bucket_index = list(b.arn for b in all_buckets).index(token_arn)
            start = last_bucket_index + 1
        else:
            start = 0

        buckets = all_buckets[start : start + max_buckets]

        next_continuation_token = None
        if start + max_buckets < len(all_buckets):
            next_continuation_token = b64encode(
                f"{buckets[-1].arn}|{prefix if prefix else ''}".encode()
            ).decode()

        return buckets, next_continuation_token

    def get_table_bucket(self, table_bucket_arn: str) -> FakeTableBucket:
        bucket = self.table_buckets.get(table_bucket_arn)
        if not bucket:
            raise NotFoundException("The specified bucket does not exist.")
        return bucket

    def delete_table_bucket(self, table_bucket_arn: str) -> None:
        # make sure table exists first
        self.get_table_bucket(table_bucket_arn)
        self.table_buckets.pop(table_bucket_arn)

    def create_namespace(self, table_bucket_arn: str, namespace: str) -> Namespace:
        bucket = self.table_buckets.get(table_bucket_arn)

        if not bucket:
            raise NotFoundException(
                "The request was rejected because the specified resource could not be found."
            )

        if namespace in bucket.namespaces:
            raise ConflictException(
                "A namespace with an identical name already exists in the bucket."
            )

        ns = Namespace(
            namespace, account_id=self.account_id, created_by=self.account_id
        )
        bucket.namespaces[ns.name] = ns
        return ns

    def list_namespaces(
        self,
        table_bucket_arn: str,
        prefix: Optional[str] = None,
        continuation_token: Optional[str] = None,
        max_namespaces: Optional[int] = None,
    ) -> Tuple[List[Namespace], Optional[str]]:
        bucket = self.get_table_bucket(table_bucket_arn)

        if not max_namespaces:
            max_namespaces = S3TABLES_DEFAULT_MAX_NAMESPACES

        all_namespaces = list(
            ns
            for ns in bucket.namespaces.values()
            if (prefix is None or ns.name.startswith(prefix))
        )

        # encode bucket arn in the continuation_token together with prefix value
        # raise invalidcontinuationtoken if the prefix changed
        if continuation_token:
            # expect continuation token to be b64encoded
            ns_name, table_bucket, token_prefix = (
                b64decode(continuation_token.encode()).decode("utf-8").split("|")
            )
            if token_prefix and token_prefix != prefix:
                raise InvalidContinuationToken()
            if table_bucket != table_bucket_arn:
                raise InvalidContinuationToken()
            last_namespace_index = list(ns.name for ns in all_namespaces).index(ns_name)
            start = last_namespace_index + 1
        else:
            start = 0

        namespaces = all_namespaces[start : start + max_namespaces]

        next_continuation_token = None
        if start + max_namespaces < len(all_namespaces):
            next_continuation_token = b64encode(
                f"{namespaces[-1].name}|{table_bucket_arn}|{prefix if prefix else ''}".encode()
            ).decode()
        # implement here
        return namespaces, next_continuation_token

    def get_namespace(self, table_bucket_arn: str, namespace: str) -> Namespace:
        bucket = self.table_buckets.get(table_bucket_arn)
        if bucket and namespace in bucket.namespaces:
            return bucket.namespaces[namespace]

        raise NotFoundException(
            "The request was rejected because the specified resource could not be found."
        )

    def delete_namespace(self, table_bucket_arn: str, namespace: str) -> None:
        bucket = self.table_buckets.get(table_bucket_arn)
        if bucket and namespace in bucket.namespaces:
            bucket.namespaces.pop(namespace)
            return

        raise NotFoundException(
            "The request was rejected because the specified resource could not be found."
        )

    def create_table(
        self,
        table_bucket_arn: str,
        namespace: str,
        name: str,
        format: Literal["ICEBERG"],
    ) -> Table:
        bucket = self.table_buckets.get(table_bucket_arn)
        if bucket and namespace in bucket.namespaces:
            ns = bucket.namespaces[namespace]
            if name in ns.tables:
                raise ValueError("Table already exists")
            table = Table(
                name=name,
                account_id=self.account_id,
                created_by=self.account_id,
                format=format,
                namespace=namespace,
                table_bucket_arn=table_bucket_arn,
                type="customer",
                managed_by_service=False,
            )
            ns.tables[table.name] = table
            return table
        raise ValueError("resource doesnt exist")

    def get_table(self, table_bucket_arn: str, namespace: str, name: str) -> Table:
        bucket = self.table_buckets.get(table_bucket_arn)
        if bucket and namespace in bucket.namespaces:
            if name in bucket.namespaces[namespace].tables:
                return bucket.namespaces[namespace].tables[name]
        raise ValueError("table does not exist")

    def list_tables(
        self,
        table_bucket_arn: str,
        namespace: Optional[str] = None,
        prefix: Optional[str] = None,
        continuation_token: Optional[str] = None,
        max_tables: Optional[int] = None,
    ) -> Tuple[List[Table], Optional[str]]:
        bucket = self.table_buckets.get(table_bucket_arn)
        if not bucket or (namespace and namespace not in bucket.namespaces):
            raise NotFoundException(
                "The request was rejected because the specified resource could not be found."
            )

        if not max_tables:
            max_tables = S3TABLES_DEFAULT_MAX_TABLES

        if namespace:
            all_tables = list(
                table
                for table in bucket.namespaces[namespace].tables.values()
                if (prefix is None or table.name.startswith(prefix))
            )
        else:
            all_tables = list(
                table
                for ns in bucket.namespaces.values()
                for table in ns.tables.values()
                if (prefix is None or table.name.startswith(prefix))
            )

        # encode bucket arn in the continuation_token together with prefix value
        # raise invalidcontinuationtoken if the prefix changed
        if continuation_token:
            # expect continuation token to be b64encoded
            table_name, ns_name, table_bucket, token_prefix = (
                b64decode(continuation_token.encode()).decode("utf-8").split("|")
            )
            if token_prefix and token_prefix != prefix:
                raise InvalidContinuationToken()
            if table_bucket != table_bucket_arn:
                raise InvalidContinuationToken()
            if ns_name and ns_name != namespace:
                raise InvalidContinuationToken()
            last_table_index = list(table.name for table in all_tables).index(
                table_name
            )
            start = last_table_index + 1
        else:
            start = 0

        tables = all_tables[start : start + max_tables]

        next_continuation_token = None
        if start + max_tables < len(all_tables):
            next_continuation_token = b64encode(
                f"{tables[-1].name}|{namespace if namespace else ''}|{table_bucket_arn}|{prefix if prefix else ''}".encode()
            ).decode()
        return tables, next_continuation_token

    def delete_table(
        self, table_bucket_arn: str, namespace: str, name: str, version_token: str
    ) -> None:
        bucket = self.table_buckets.get(table_bucket_arn)
        if bucket and namespace in bucket.namespaces:
            ns = bucket.namespaces[namespace]
            if name in ns.tables:
                ns.tables.pop(name)
                return
        raise ValueError("Table doesn't exist")


s3tables_backends = BackendDict(
    S3TablesBackend,
    "s3tables",
    additional_regions=["us-east-1", "us-east-2", "us-west-2"],
)
