from __future__ import unicode_literals
from .models import s3bucket_path_backend

from .utils import bucket_name_from_url, parse_key_name, is_delete_keys

from moto.s3.responses import ResponseObject


S3BucketPathResponseInstance = ResponseObject(
    s3bucket_path_backend,
    bucket_name_from_url,
    parse_key_name,
    is_delete_keys,
)
