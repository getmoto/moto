from moto.core.exceptions import RESTError

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

    def __init__(self, **kwargs):
        kwargs.setdefault("template", "error")
        self.templates["error"] = EXCEPTION_RESPONSE
        super().__init__(**kwargs)


class OriginDoesNotExist(CloudFrontException):

    code = 404

    def __init__(self, **kwargs):
        kwargs["error_type"] = "NoSuchOrigin"
        kwargs["message"] = "One or more of your origins or origin groups do not exist."
        super().__init__(**kwargs)


class InvalidOriginServer(CloudFrontException):
    def __init__(self, **kwargs):
        kwargs["error_type"] = "InvalidOrigin"
        kwargs[
            "message"
        ] = "The specified origin server does not exist or is not valid."
        super().__init__(**kwargs)


class DomainNameNotAnS3Bucket(CloudFrontException):
    def __init__(self, **kwargs):
        kwargs["error_type"] = "InvalidArgument"
        kwargs[
            "message"
        ] = "The parameter Origin DomainName does not refer to a valid S3 bucket."
        super().__init__(**kwargs)


class DistributionAlreadyExists(CloudFrontException):
    def __init__(self, dist_id, **kwargs):
        kwargs["error_type"] = "DistributionAlreadyExists"
        kwargs[
            "message"
        ] = f"The caller reference that you are using to create a distribution is associated with another distribution. Already exists: {dist_id}"
        super().__init__(**kwargs)


class InvalidIfMatchVersion(CloudFrontException):
    def __init__(self, **kwargs):
        kwargs["error_type"] = "InvalidIfMatchVersion"
        kwargs[
            "message"
        ] = "The If-Match version is missing or not valid for the resource."
        super().__init__(**kwargs)


class NoSuchDistribution(CloudFrontException):

    code = 404

    def __init__(self, **kwargs):
        kwargs["error_type"] = "NoSuchDistribution"
        kwargs["message"] = "The specified distribution does not exist."
        super().__init__(**kwargs)
