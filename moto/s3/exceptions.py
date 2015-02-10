from __future__ import unicode_literals
from moto.core.exceptions import RESTError


ERROR_WITH_BUCKET_NAME = """{% extends 'error' %}
{% block extra %}<BucketName>{{ bucket }}</BucketName>{% endblock %}
"""


class S3ClientError(RESTError):
    pass


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
