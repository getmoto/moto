from moto.core.exceptions import RESTError
from typing import Any

EXCEPTION_RESPONSE = """<?xml version="1.0"?>
<ErrorResponse xmlns="http://cloudfront.amazonaws.com/doc/2020-05-31/">
  <Error>
    <Type>Sender</Type>
    <Code>{{ error_type }}</Code>
    <Message>{{ message }}</Message>
  </Error>
  <{{ request_id_tag }}>30c0dedb-92b1-4e2b-9be4-1188e3ed86ab</{{ request_id_tag }}>
</ErrorResponse>"""


class CloudFrontException(RESTError):

    code = 400

    def __init__(self, error_type: str, message: str, **kwargs: Any):
        kwargs.setdefault("template", "cferror")
        self.templates["cferror"] = EXCEPTION_RESPONSE
        super().__init__(error_type, message, **kwargs)


class OriginDoesNotExist(CloudFrontException):

    code = 404

    def __init__(self) -> None:
        super().__init__(
            "NoSuchOrigin",
            message="One or more of your origins or origin groups do not exist.",
        )


class InvalidOriginServer(CloudFrontException):
    def __init__(self) -> None:
        super().__init__(
            "InvalidOrigin",
            message="The specified origin server does not exist or is not valid.",
        )


class DomainNameNotAnS3Bucket(CloudFrontException):
    def __init__(self) -> None:
        super().__init__(
            "InvalidArgument",
            message="The parameter Origin DomainName does not refer to a valid S3 bucket.",
        )


class DistributionAlreadyExists(CloudFrontException):
    def __init__(self, dist_id: str):
        super().__init__(
            "DistributionAlreadyExists",
            message=f"The caller reference that you are using to create a distribution is associated with another distribution. Already exists: {dist_id}",
        )


class InvalidIfMatchVersion(CloudFrontException):
    def __init__(self) -> None:
        super().__init__(
            "InvalidIfMatchVersion",
            message="The If-Match version is missing or not valid for the resource.",
        )


class NoSuchDistribution(CloudFrontException):

    code = 404

    def __init__(self) -> None:
        super().__init__(
            "NoSuchDistribution", message="The specified distribution does not exist."
        )
