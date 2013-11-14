from moto.s3.models import S3Backend


class S3BucketPathBackend(S3Backend):
    True

s3bucket_path_backend = S3BucketPathBackend()
