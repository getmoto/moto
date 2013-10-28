from .models import s3bucket_path_backend

from .utils import bucket_name_from_url

from moto.s3.responses import ResponseObject


def parse_key_name(pth):
    return "/".join(pth.rstrip("/").split("/")[2:])

S3BucketPathResponseInstance = ResponseObject(
    s3bucket_path_backend,
    bucket_name_from_url,
    parse_key_name,
)
