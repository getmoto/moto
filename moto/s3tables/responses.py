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
        return s3tables_backends[self.current_account][self.region]

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
        table_bucket_arn = unquote(self.path).lstrip("/").split("/", 1)[-1]
        bucket = self.s3tables_backend.get_table_bucket(
            table_bucket_arn=table_bucket_arn,
        )

        return (
            200,
            self.default_response_headers,
            json.dumps(
                dict(
                    arn=bucket.arn,
                    name=bucket.name,
                    ownerAccountId=bucket.account_id,
                    createdAt=bucket.creation_date.isoformat(),
                )
            ),
        )

    def delete_table_bucket(self) -> TYPE_RESPONSE:
        table_bucket_arn = unquote(self.path).lstrip("/").split("/", 1)[-1]
        self.s3tables_backend.delete_table_bucket(
            table_bucket_arn=table_bucket_arn,
        )

        return 204, {}, ""

    def create_namespace(self):
        table_bucket_arn = unquote(self.path).lstrip("/").split("/", 1)[-1]
        name = json.loads(self.body)["namespace"][0]
        namespace = self.s3tables_backend.create_namespace(
            table_bucket_arn=table_bucket_arn,
            namespace=name,
        )
        return (
            200,
            self.default_response_headers,
            json.dumps(
                dict(tableBucketArn=table_bucket_arn, namespace=[namespace.name])
            ),
        )

    def list_namespaces(self):
        table_bucket_arn = unquote(self.path).lstrip("/").split("/", 1)[-1]

        params = self._get_params()
        continuation_token = params.get("continuationToken")
        max_namespaces = params.get("maxNamespaces")
        prefix = params.get("prefix")

        namespaces, continuation_token = self.s3tables_backend.list_namespaces(
            table_bucket_arn=table_bucket_arn,
            prefix=prefix,
            continuation_token=continuation_token,
            max_namespaces=int(max_namespaces) if max_namespaces else None,
        )

        body: Dict[str, Any] = {
            "namespaces": [
                {

                    "namespace": [ns.name],
                    "createdAt": ns.creation_date.isoformat(),
                    "createdBy": ns.created_by,
                    "ownerAccountId": ns.account_id,
                }
                for ns in namespaces
            ]
        }
        if continuation_token:
            body.update(continuationToken=continuation_token)

        return 200, self.default_response_headers, json.dumps(body)

    def get_namespace(self):
        _, table_bucket_arn, namespace = self.path.lstrip("/").split("/")
        table_bucket_arn = unquote(table_bucket_arn)
        namespace = self.s3tables_backend.get_namespace(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
        )
        return (
            200,
            self.default_response_headers,
            json.dumps(
                dict(
                    namespace=[namespace.name],
                    createdAt=namespace.creation_date.isoformat(),
                    createdBy=namespace.created_by,
                    ownerAccountId=namespace.account_id,
                )
            ),
        )

    def delete_namespace(self):
        params = self._get_params()
        table_bucket_arn = params.get("tableBucketARN")
        namespace = params.get("namespace")
        self.s3tables_backend.delete_namespace(
            table_bucket_arn=table_bucket_arn,
            namespace=namespace,
        )
        # TODO: adjust response
        return json.dumps(dict())
