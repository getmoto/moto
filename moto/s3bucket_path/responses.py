from .models import s3bucket_path_backend

from .utils import bucket_name_from_url

from moto.s3.responses import S3_ALL_BUCKETS, S3_BUCKET_GET_RESPONSE, \
     S3_BUCKET_CREATE_RESPONSE, S3_DELETE_BUCKET_SUCCESS, \
     S3_DELETE_NON_EXISTING_BUCKET, S3_DELETE_BUCKET_WITH_ITEMS_ERROR, \
     S3_DELETE_OBJECT_SUCCESS, S3_OBJECT_RESPONSE, S3_OBJECT_COPY_RESPONSE, \
     ResponseObject

def parse_key_name(pth):
    return "/".join(pth.rstrip("/").split("/")[2:])

S3BucketPathResponseInstance = ResponseObject(s3bucket_path_backend,
    bucket_name_from_url, parse_key_name)
