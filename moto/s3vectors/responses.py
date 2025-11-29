"""Handles incoming s3vectors requests, invokes methods, returns responses."""

from moto.core.responses import ActionResult, BaseResponse, EmptyResult, get_partition

from .exceptions import (
    ValidationError,
    VectorBucketInvalidChars,
    VectorBucketInvalidLength,
)
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

    def create_index(self) -> ActionResult:
        vector_bucket_name = self._get_param("vectorBucketName")
        vector_bucket_arn = self._get_param("vectorBucketArn")
        index_name = self._get_param("indexName")
        data_type = self._get_param("dataType")
        dimension = self._get_param("dimension")
        distance_metric = self._get_param("distanceMetric")

        if data_type not in ["float32"]:
            raise ValidationError(
                "1 validation error detected. Value at '/dataType' failed to satisfy constraint: Member must satisfy enum value set: [float32]"
            )
        if dimension < 1 or dimension >= 4096:
            raise ValidationError(
                "1 validation error detected. Value at '/dimension' failed to satisfy constraint: Member must be between 1 and 4096, inclusive"
            )
        if distance_metric not in ["euclidean", "cosine"]:
            raise ValidationError(
                "1 validation error detected. Value at '/distanceMetric' failed to satisfy constraint: Member must satisfy enum value set: [euclidean, cosine]"
            )

        self.s3vectors_backend.create_index(
            vector_bucket_name=vector_bucket_name,
            vector_bucket_arn=vector_bucket_arn,
            index_name=index_name,
            data_type=data_type,
            dimension=dimension,
            distance_metric=distance_metric,
        )
        return EmptyResult()

    def delete_index(self) -> ActionResult:
        vector_bucket_name = self._get_param("vectorBucketName")
        index_name = self._get_param("indexName")
        index_arn = self._get_param("indexArn")
        self.s3vectors_backend.delete_index(
            vector_bucket_name=vector_bucket_name,
            index_name=index_name,
            index_arn=index_arn,
        )
        return EmptyResult()

    def get_index(self) -> ActionResult:
        vector_bucket_name = self._get_param("vectorBucketName")
        index_name = self._get_param("indexName")
        index_arn = self._get_param("indexArn")

        if vector_bucket_name and index_arn:
            raise ValidationError(
                "Must specify either indexArn or both vectorBucketName and indexName"
            )

        index = self.s3vectors_backend.get_index(
            vector_bucket_name=vector_bucket_name,
            index_name=index_name,
            index_arn=index_arn,
        )
        return ActionResult(result={"index": index})

    def list_indexes(self) -> ActionResult:
        vector_bucket_name = self._get_param("vectorBucketName")
        vector_bucket_arn = self._get_param("vectorBucketArn")

        if vector_bucket_name and vector_bucket_arn:
            raise ValidationError(
                "Must specify either vectorBucketName or vectorBucketArn but not both"
            )

        indexes = self.s3vectors_backend.list_indexes(
            vector_bucket_name=vector_bucket_name,
            vector_bucket_arn=vector_bucket_arn,
        )
        return ActionResult(result={"indexes": indexes})

    def delete_vector_bucket_policy(self) -> ActionResult:
        vector_bucket_name = self._get_param("vectorBucketName")
        vector_bucket_arn = self._get_param("vectorBucketArn")

        if vector_bucket_name and vector_bucket_arn:
            raise ValidationError(
                "Must specify either vectorBucketName or vectorBucketArn but not both"
            )

        self.s3vectors_backend.delete_vector_bucket_policy(
            vector_bucket_name=vector_bucket_name,
            vector_bucket_arn=vector_bucket_arn,
        )
        return EmptyResult()

    def get_vector_bucket_policy(self) -> ActionResult:
        vector_bucket_name = self._get_param("vectorBucketName")
        vector_bucket_arn = self._get_param("vectorBucketArn")

        if vector_bucket_name and vector_bucket_arn:
            raise ValidationError(
                "Must specify either vectorBucketName or vectorBucketArn but not both"
            )

        policy = self.s3vectors_backend.get_vector_bucket_policy(
            vector_bucket_name=vector_bucket_name,
            vector_bucket_arn=vector_bucket_arn,
        )
        return ActionResult(result={"policy": policy})

    def put_vector_bucket_policy(self) -> ActionResult:
        vector_bucket_name = self._get_param("vectorBucketName")
        vector_bucket_arn = self._get_param("vectorBucketArn")

        if vector_bucket_name and vector_bucket_arn:
            raise ValidationError(
                "Must specify either vectorBucketName or vectorBucketArn but not both"
            )

        vector_bucket_policy = self._get_param("policy")
        self.s3vectors_backend.put_vector_bucket_policy(
            vector_bucket_name=vector_bucket_name,
            vector_bucket_arn=vector_bucket_arn,
            policy=vector_bucket_policy,
        )
        return EmptyResult()
