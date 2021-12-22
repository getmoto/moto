"""Exceptions raised by the s3control service."""
from moto.s3.exceptions import S3ClientError


class NoSuchPublicAccessBlockConfiguration(S3ClientError):
    code = 404

    def __init__(self, *args, **kwargs):
        super(NoSuchPublicAccessBlockConfiguration, self).__init__(
            "NoSuchPublicAccessBlockConfiguration",
            "The public access block configuration was not found",
            *args,
            **kwargs,
        )


class InvalidPublicAccessBlockConfiguration(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidPublicAccessBlockConfiguration, self).__init__(
            "InvalidRequest",
            "Must specify at least one configuration.",
            *args,
            **kwargs,
        )


class WrongPublicAccessBlockAccountIdError(S3ClientError):
    code = 403

    def __init__(self):
        super(WrongPublicAccessBlockAccountIdError, self).__init__(
            "AccessDenied", "Access Denied"
        )
