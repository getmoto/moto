from __future__ import unicode_literals

from moto.core.exceptions import RESTError

ERROR_WITH_BUCKET_NAME = """{% extends 'single_error' %}
{% block extra %}<BucketName>{{ bucket }}</BucketName>{% endblock %}
"""

ERROR_WITH_KEY_NAME = """{% extends 'single_error' %}
{% block extra %}<KeyName>{{ key_name }}</KeyName>{% endblock %}
"""

ERROR_WITH_CONDITION_NAME = """{% extends 'single_error' %}
{% block extra %}<Condition>{{ condition }}</Condition>{% endblock %}
"""

ERROR_WITH_RANGE = """{% extends 'single_error' %}
{% block extra %}<ActualObjectSize>{{ actual_size }}</ActualObjectSize>
<RangeRequested>{{ range_requested }}</RangeRequested>{% endblock %}
"""


class S3ClientError(RESTError):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template", "single_error")
        self.templates["bucket_error"] = ERROR_WITH_BUCKET_NAME
        super(S3ClientError, self).__init__(*args, **kwargs)


class BucketError(S3ClientError):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("template", "bucket_error")
        self.templates["bucket_error"] = ERROR_WITH_BUCKET_NAME
        super(BucketError, self).__init__(*args, **kwargs)


class BucketAlreadyExists(BucketError):
    code = 409

    def __init__(self, *args, **kwargs):
        super(BucketAlreadyExists, self).__init__(
            "BucketAlreadyExists",
            (
                "The requested bucket name is not available. The bucket "
                "namespace is shared by all users of the system. Please "
                "select a different name and try again"
            ),
            *args,
            **kwargs
        )


class MissingBucket(BucketError):
    code = 404

    def __init__(self, *args, **kwargs):
        super(MissingBucket, self).__init__(
            "NoSuchBucket", "The specified bucket does not exist", *args, **kwargs
        )


class MissingKey(S3ClientError):
    code = 404

    def __init__(self, key_name):
        super(MissingKey, self).__init__(
            "NoSuchKey", "The specified key does not exist.", Key=key_name
        )


class ObjectNotInActiveTierError(S3ClientError):
    code = 403

    def __init__(self, key_name):
        super(ObjectNotInActiveTierError, self).__init__(
            "ObjectNotInActiveTierError",
            "The source object of the COPY operation is not in the active tier and is only stored in Amazon Glacier.",
            Key=key_name,
        )


class InvalidPartOrder(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidPartOrder, self).__init__(
            "InvalidPartOrder",
            (
                "The list of parts was not in ascending order. The parts "
                "list must be specified in order by part number."
            ),
            *args,
            **kwargs
        )


class InvalidPart(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidPart, self).__init__(
            "InvalidPart",
            (
                "One or more of the specified parts could not be found. "
                "The part might not have been uploaded, or the specified "
                "entity tag might not have matched the part's entity tag."
            ),
            *args,
            **kwargs
        )


class EntityTooSmall(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(EntityTooSmall, self).__init__(
            "EntityTooSmall",
            "Your proposed upload is smaller than the minimum allowed object size.",
            *args,
            **kwargs
        )


class InvalidRequest(S3ClientError):
    code = 400

    def __init__(self, method, *args, **kwargs):
        super(InvalidRequest, self).__init__(
            "InvalidRequest",
            "Found unsupported HTTP method in CORS config. Unsupported method is {}".format(
                method
            ),
            *args,
            **kwargs
        )


class IllegalLocationConstraintException(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(IllegalLocationConstraintException, self).__init__(
            "IllegalLocationConstraintException",
            "The unspecified location constraint is incompatible for the region specific endpoint this request was sent to.",
            *args,
            **kwargs
        )


class MalformedXML(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(MalformedXML, self).__init__(
            "MalformedXML",
            "The XML you provided was not well-formed or did not validate against our published schema",
            *args,
            **kwargs
        )


class MalformedACLError(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(MalformedACLError, self).__init__(
            "MalformedACLError",
            "The XML you provided was not well-formed or did not validate against our published schema",
            *args,
            **kwargs
        )


class InvalidTargetBucketForLogging(S3ClientError):
    code = 400

    def __init__(self, msg):
        super(InvalidTargetBucketForLogging, self).__init__(
            "InvalidTargetBucketForLogging", msg
        )


class CrossLocationLoggingProhibitted(S3ClientError):
    code = 403

    def __init__(self):
        super(CrossLocationLoggingProhibitted, self).__init__(
            "CrossLocationLoggingProhibitted", "Cross S3 location logging not allowed."
        )


class InvalidNotificationARN(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidNotificationARN, self).__init__(
            "InvalidArgument", "The ARN is not well formed", *args, **kwargs
        )


class InvalidNotificationDestination(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidNotificationDestination, self).__init__(
            "InvalidArgument",
            "The notification destination service region is not valid for the bucket location constraint",
            *args,
            **kwargs
        )


class InvalidNotificationEvent(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidNotificationEvent, self).__init__(
            "InvalidArgument",
            "The event is not supported for notifications",
            *args,
            **kwargs
        )


class InvalidStorageClass(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidStorageClass, self).__init__(
            "InvalidStorageClass",
            "The storage class you specified is not valid",
            *args,
            **kwargs
        )


class InvalidBucketName(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidBucketName, self).__init__(
            "InvalidBucketName", "The specified bucket is not valid.", *args, **kwargs
        )


class DuplicateTagKeys(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(DuplicateTagKeys, self).__init__(
            "InvalidTag",
            "Cannot provide multiple Tags with the same key",
            *args,
            **kwargs
        )


class S3AccessDeniedError(S3ClientError):
    code = 403

    def __init__(self, *args, **kwargs):
        super(S3AccessDeniedError, self).__init__(
            "AccessDenied", "Access Denied", *args, **kwargs
        )


class BucketAccessDeniedError(BucketError):
    code = 403

    def __init__(self, *args, **kwargs):
        super(BucketAccessDeniedError, self).__init__(
            "AccessDenied", "Access Denied", *args, **kwargs
        )


class S3InvalidTokenError(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(S3InvalidTokenError, self).__init__(
            "InvalidToken",
            "The provided token is malformed or otherwise invalid.",
            *args,
            **kwargs
        )


class BucketInvalidTokenError(BucketError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(BucketInvalidTokenError, self).__init__(
            "InvalidToken",
            "The provided token is malformed or otherwise invalid.",
            *args,
            **kwargs
        )


class S3InvalidAccessKeyIdError(S3ClientError):
    code = 403

    def __init__(self, *args, **kwargs):
        super(S3InvalidAccessKeyIdError, self).__init__(
            "InvalidAccessKeyId",
            "The AWS Access Key Id you provided does not exist in our records.",
            *args,
            **kwargs
        )


class BucketInvalidAccessKeyIdError(S3ClientError):
    code = 403

    def __init__(self, *args, **kwargs):
        super(BucketInvalidAccessKeyIdError, self).__init__(
            "InvalidAccessKeyId",
            "The AWS Access Key Id you provided does not exist in our records.",
            *args,
            **kwargs
        )


class S3SignatureDoesNotMatchError(S3ClientError):
    code = 403

    def __init__(self, *args, **kwargs):
        super(S3SignatureDoesNotMatchError, self).__init__(
            "SignatureDoesNotMatch",
            "The request signature we calculated does not match the signature you provided. Check your key and signing method.",
            *args,
            **kwargs
        )


class BucketSignatureDoesNotMatchError(S3ClientError):
    code = 403

    def __init__(self, *args, **kwargs):
        super(BucketSignatureDoesNotMatchError, self).__init__(
            "SignatureDoesNotMatch",
            "The request signature we calculated does not match the signature you provided. Check your key and signing method.",
            *args,
            **kwargs
        )


class NoSuchPublicAccessBlockConfiguration(S3ClientError):
    code = 404

    def __init__(self, *args, **kwargs):
        super(NoSuchPublicAccessBlockConfiguration, self).__init__(
            "NoSuchPublicAccessBlockConfiguration",
            "The public access block configuration was not found",
            *args,
            **kwargs
        )


class InvalidPublicAccessBlockConfiguration(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidPublicAccessBlockConfiguration, self).__init__(
            "InvalidRequest",
            "Must specify at least one configuration.",
            *args,
            **kwargs
        )


class WrongPublicAccessBlockAccountIdError(S3ClientError):
    code = 403

    def __init__(self):
        super(WrongPublicAccessBlockAccountIdError, self).__init__(
            "AccessDenied", "Access Denied"
        )


class NoSystemTags(S3ClientError):
    code = 400

    def __init__(self):
        super(NoSystemTags, self).__init__(
            "InvalidTag", "System tags cannot be added/updated by requester"
        )


class NoSuchUpload(S3ClientError):
    code = 404

    def __init__(self):
        super(NoSuchUpload, self).__init__(
            "NoSuchUpload", "The specified multipart upload does not exist."
        )


class PreconditionFailed(S3ClientError):
    code = 412

    def __init__(self, failed_condition, **kwargs):
        kwargs.setdefault("template", "condition_error")
        self.templates["condition_error"] = ERROR_WITH_CONDITION_NAME
        super(PreconditionFailed, self).__init__(
            "PreconditionFailed",
            "At least one of the pre-conditions you specified did not hold",
            condition=failed_condition,
            **kwargs
        )


class InvalidRange(S3ClientError):
    code = 416

    def __init__(self, range_requested, actual_size, **kwargs):
        kwargs.setdefault("template", "range_error")
        self.templates["range_error"] = ERROR_WITH_RANGE
        super(InvalidRange, self).__init__(
            "InvalidRange",
            "The requested range is not satisfiable",
            range_requested=range_requested,
            actual_size=actual_size,
            **kwargs
        )
