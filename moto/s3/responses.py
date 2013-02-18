from jinja2 import Template

from .models import s3_backend

def bucket_response(uri, body, headers):
    hostname = uri.hostname
    bucket_name = hostname.replace(".s3.amazonaws.com", "")

    if uri.method == 'GET':
        bucket = s3_backend.get_bucket(bucket_name)
        if bucket:
            template = Template(S3_BUCKET_GET_RESPONSE)
            return template.render(bucket=bucket)
        else:
            return "", dict(status=404)
    else:
        new_bucket = s3_backend.create_bucket(bucket_name)
        template = Template(S3_BUCKET_CREATE_RESPONSE)
        return template.render(bucket=new_bucket)


def key_response(uri_info, body, headers):

    key_name = uri_info.path.lstrip('/')
    hostname = uri_info.hostname
    bucket_name = hostname.replace(".s3.amazonaws.com", "")

    if uri_info.method == 'GET':
        key = s3_backend.get_key(bucket_name, key_name)
        if key:
            return key.value
        else:
            return "", dict(status=404)

    if uri_info.method == 'PUT':
        if body:
            new_key = s3_backend.set_key(bucket_name, key_name, body)
            return S3_OBJECT_RESPONSE, dict(etag=new_key.etag)
        key = s3_backend.get_key(bucket_name, key_name)
        if key:
            return "", dict(etag=key.etag)
        else:
            return ""
    elif uri_info.method == 'HEAD':
        key = s3_backend.get_key(bucket_name, key_name)
        return S3_OBJECT_RESPONSE, dict(etag=key.etag)
    else:
        import pdb;pdb.set_trace()


S3_BUCKET_GET_RESPONSE = """<ListBucket xmlns="http://doc.s3.amazonaws.com/2006-03-01">\
      <Bucket>{{ bucket.name }}</Bucket>\
      <Prefix>notes/</Prefix>\
      <Delimiter>/</Delimiter>\
      <MaxKeys>1000</MaxKeys>\
      <AWSAccessKeyId>AKIAIOSFODNN7EXAMPLE</AWSAccessKeyId>\
      <Timestamp>2006-03-01T12:00:00.183Z</Timestamp>\
      <Signature>Iuyz3d3P0aTou39dzbqaEXAMPLE=</Signature>\
    </ListBucket>"""

S3_BUCKET_CREATE_RESPONSE = """<CreateBucketResponse xmlns="http://s3.amazonaws.com/doc/2006-03-01">
  <CreateBucketResponse>
    <Bucket>{{ bucket.name }}</Bucket>
  </CreateBucketResponse>
</CreateBucketResponse>"""

S3_OBJECT_RESPONSE = """<PutObjectResponse xmlns="http://s3.amazonaws.com/doc/2006-03-01">
      <PutObjectResponse>
        <ETag>&quot;asdlfkdalsjfsalfkjsadlfjsdjkk&quot;</ETag>
        <LastModified>2006-03-01T12:00:00.183Z</LastModified>
      </PutObjectResponse>
    </PutObjectResponse>"""