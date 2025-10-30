"""S3VectorsBackend class with methods for supported APIs."""

from typing import Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.utilities.utils import PARTITION_NAMES

from .exceptions import VectorBucketAlreadyExists, VectorBucketNotFound
from .utils import create_vector_bucket_arn


class VectorBucket(BaseModel):
    def __init__(
        self,
        arn: str,
        name: str,
        encryption_configuration: dict[str, str],
    ):
        self.vector_bucket_name = name
        self.vector_bucket_arn = arn
        self.encryption_configuration = encryption_configuration or {
            "sseType": "AES256"
        }


class S3VectorsBackend(BaseBackend):
    """Implementation of S3Vectors APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.vector_buckets: dict[str, VectorBucket] = {}

    def create_vector_bucket(
        self,
        region: str,
        vector_bucket_name: str,
        encryption_configuration: dict[str, str],
    ) -> None:
        vector_bucket_arn = create_vector_bucket_arn(
            self.account_id, region, name=vector_bucket_name
        )
        if vector_bucket_arn in self.vector_buckets:
            raise VectorBucketAlreadyExists
        vector_bucket = VectorBucket(
            arn=vector_bucket_arn,
            name=vector_bucket_name,
            encryption_configuration=encryption_configuration,
        )
        self.vector_buckets[vector_bucket.vector_bucket_arn] = vector_bucket

    def get_vector_bucket(
        self,
        vector_bucket_name: Optional[str] = None,
        vector_bucket_arn: Optional[str] = None,
    ) -> VectorBucket:
        if vector_bucket_name:
            for vector_bucket in self.vector_buckets.values():
                if vector_bucket.vector_bucket_name == vector_bucket_name:
                    return vector_bucket
        if vector_bucket_arn and (bucket := self.vector_buckets.get(vector_bucket_arn)):
            return bucket
        raise VectorBucketNotFound

    def delete_vector_bucket(self, vector_bucket_name: str) -> None:
        if vector_bucket_name:
            try:
                bucket = self.get_vector_bucket(vector_bucket_name=vector_bucket_name)
                self.vector_buckets.pop(bucket.vector_bucket_arn, None)
            except VectorBucketNotFound:
                pass

    def list_vector_buckets(self, prefix: Optional[str]) -> list[VectorBucket]:
        return [
            bucket
            for bucket in self.vector_buckets.values()
            if not prefix or bucket.vector_bucket_name.startswith(prefix)
        ]


s3vectors_backends = BackendDict(
    S3VectorsBackend,
    "s3vectors",
    use_boto3_regions=False,
    additional_regions=PARTITION_NAMES,
)
