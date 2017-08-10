from __future__ import unicode_literals
from moto.core.exceptions import RESTError


ERROR_WITH_BUCKET_NAME = """{% extends 'single_error' %}
{% block extra %}<BucketName>{{ bucket }}</BucketName>{% endblock %}
"""

ERROR_WITH_KEY_NAME = """{% extends 'single_error' %}
{% block extra %}<KeyName>{{ key_name }}</KeyName>{% endblock %}
"""


class S3ClientError(RESTError):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('template', 'single_error')
        self.templates['bucket_error'] = ERROR_WITH_BUCKET_NAME
        super(S3ClientError, self).__init__(*args, **kwargs)


class BucketError(S3ClientError):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('template', 'bucket_error')
        self.templates['bucket_error'] = ERROR_WITH_BUCKET_NAME
        super(BucketError, self).__init__(*args, **kwargs)


class BucketAlreadyExists(BucketError):
    code = 409

    def __init__(self, *args, **kwargs):
        super(BucketAlreadyExists, self).__init__(
            "BucketAlreadyExists",
            ("The requested bucket name is not available. The bucket "
             "namespace is shared by all users of the system. Please "
             "select a different name and try again"),
            *args, **kwargs)


class MissingBucket(BucketError):
    code = 404

    def __init__(self, *args, **kwargs):
        super(MissingBucket, self).__init__(
            "NoSuchBucket",
            "The specified bucket does not exist",
            *args, **kwargs)


class MissingKey(S3ClientError):
    code = 404

    def __init__(self, key_name):
        super(MissingKey, self).__init__(
            "NoSuchKey",
            "The specified key does not exist.",
            Key=key_name,
        )


class InvalidPartOrder(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidPartOrder, self).__init__(
            "InvalidPartOrder",
            ("The list of parts was not in ascending order. The parts "
             "list must be specified in order by part number."),
            *args, **kwargs)


class InvalidPart(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(InvalidPart, self).__init__(
            "InvalidPart",
            ("One or more of the specified parts could not be found. "
             "The part might not have been uploaded, or the specified "
             "entity tag might not have matched the part's entity tag."),
            *args, **kwargs)


class EntityTooSmall(S3ClientError):
    code = 400

    def __init__(self, *args, **kwargs):
        super(EntityTooSmall, self).__init__(
            "EntityTooSmall",
            "Your proposed upload is smaller than the minimum allowed object size.",
            *args, **kwargs)
