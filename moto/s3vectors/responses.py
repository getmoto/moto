"""Handles incoming s3vectors requests, invokes methods, returns responses."""

from moto.core.responses import ActionResult, BaseResponse, EmptyResult, get_partition

from .exceptions import VectorBucketInvalidChars, VectorBucketInvalidLength
from .models import S3VectorsBackend, s3vectors_backends

# Some obvious invalid chars - but I haven't found an official list (or even a allowed regex, which would be easier)
INVALID_BUCKET_NAME_CHARACTERS = ["&", "_"]


class S3VectorsResponse(BaseResponse):
    """Handler for S3Vectors requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="s3vectors")

    @property
    def s3vectors_backend(self) -> S3VectorsBackend:
        return s3vectors_backends[self.current_account][get_partition(self.region)]

    def create_vector_bucket(self) -> ActionResult:
        vector_bucket_name = self._get_param("vectorBucketName")
        encryption_configuration = self._get_param("encryptionConfiguration")

        if not 2 < len(vector_bucket_name) < 64:
            raise VectorBucketInvalidLength(length=len(vector_bucket_name))
        if any(char in vector_bucket_name for char in INVALID_BUCKET_NAME_CHARACTERS):
            raise VectorBucketInvalidChars

        self.s3vectors_backend.create_vector_bucket(
            region=self.region,
            vector_bucket_name=vector_bucket_name,
            encryption_configuration=encryption_configuration,
        )
        return EmptyResult()

    def delete_vector_bucket(self) -> ActionResult:
        vector_bucket_name = self._get_param("vectorBucketName")
        self.s3vectors_backend.delete_vector_bucket(
            vector_bucket_name=vector_bucket_name,
        )
        return EmptyResult()

    def get_vector_bucket(self) -> ActionResult:
        vector_bucket_name = self._get_param("vectorBucketName")
        vector_bucket_arn = self._get_param("vectorBucketArn")
        bucket = self.s3vectors_backend.get_vector_bucket(
            vector_bucket_name=vector_bucket_name,
            vector_bucket_arn=vector_bucket_arn,
        )
        return ActionResult(result={"vectorBucket": bucket})

    def list_vector_buckets(self) -> ActionResult:
        prefix = self._get_param("prefix")
        buckets = self.s3vectors_backend.list_vector_buckets(
            prefix=prefix,
        )
        return ActionResult(result={"vectorBuckets": buckets})
