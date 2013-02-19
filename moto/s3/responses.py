from jinja2 import Template

from .models import s3_backend
from .utils import bucket_name_from_hostname


def all_buckets(uri, body, method):
    # No bucket specified. Listing all buckets
    all_buckets = s3_backend.get_all_buckets()
    template = Template(S3_ALL_BUCKETS)
    return template.render(buckets=all_buckets)


def bucket_response(uri, body, headers):
    hostname = uri.hostname
    method = uri.method

    bucket_name = bucket_name_from_hostname(hostname)

    if method == 'GET':
        bucket = s3_backend.get_bucket(bucket_name)
        if bucket:
            template = Template(S3_BUCKET_GET_RESPONSE)
            return template.render(bucket=bucket)
        else:
            return "", dict(status=404)
    elif method == 'PUT':
        new_bucket = s3_backend.create_bucket(bucket_name)
        template = Template(S3_BUCKET_CREATE_RESPONSE)
        return template.render(bucket=new_bucket)
    elif method == 'DELETE':
        removed_bucket = s3_backend.delete_bucket(bucket_name)
        if removed_bucket is None:
            # Non-existant bucket
            template = Template(S3_DELETE_NON_EXISTING_BUCKET)
            return template.render(bucket_name=bucket_name), dict(status=404)
        elif removed_bucket:
            # Bucket exists
            template = Template(S3_DELETE_BUCKET_SUCCESS)
            return template.render(bucket=removed_bucket), dict(status=204)
        else:
            # Tried to delete a bucket that still has keys
            template = Template(S3_DELETE_BUCKET_WITH_ITEMS_ERROR)
            return template.render(bucket=removed_bucket), dict(status=409)
    else:
        import pdb;pdb.set_trace()


def key_response(uri_info, body, headers):

    key_name = uri_info.path.lstrip('/')
    hostname = uri_info.hostname
    method = uri_info.method

    bucket_name = bucket_name_from_hostname(hostname)

    if method == 'GET':
        key = s3_backend.get_key(bucket_name, key_name)
        return key.value

    if method == 'PUT':
        if body:
            new_key = s3_backend.set_key(bucket_name, key_name, body)
            return S3_OBJECT_RESPONSE, dict(etag=new_key.etag)
        key = s3_backend.get_key(bucket_name, key_name)
        if key:
            return "", dict(etag=key.etag)
        else:
            return ""
    elif method == 'HEAD':
        key = s3_backend.get_key(bucket_name, key_name)
        if key:
            return S3_OBJECT_RESPONSE, dict(etag=key.etag)
        else:
            return "", dict(status=404)
    elif method == 'DELETE':
        removed_key = s3_backend.delete_key(bucket_name, key_name)
        template = Template(S3_DELETE_OBJECT_SUCCESS)
        return template.render(bucket=removed_key), dict(status=204)
    else:
        import pdb;pdb.set_trace()


S3_ALL_BUCKETS = """<ListAllMyBucketsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01">
  <Owner>
    <ID>bcaf1ffd86f41161ca5fb16fd081034f</ID>
    <DisplayName>webfile</DisplayName>
  </Owner>
  <Buckets>
    {% for bucket in buckets %}
      <Bucket>
        <Name>{{ bucket.name }}</Name>
        <CreationDate>2006-02-03T16:45:09.000Z</CreationDate>
      </Bucket>
    {% endfor %}
 </Buckets>
</ListAllMyBucketsResult>"""

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

S3_DELETE_BUCKET_SUCCESS = """<DeleteBucketResponse xmlns="http://s3.amazonaws.com/doc/2006-03-01">
  <DeleteBucketResponse>
    <Code>204</Code>
    <Description>No Content</Description>
  </DeleteBucketResponse>
</DeleteBucketResponse>"""

S3_DELETE_NON_EXISTING_BUCKET = """<?xml version="1.0" encoding="UTF-8"?>
<Error><Code>NoSuchBucket</Code>
<Message>The specified bucket does not exist</Message>
<BucketName>{{ bucket_name }}</BucketName>
<RequestId>asdfasdfsadf</RequestId>
<HostId>asfasdfsfsafasdf</HostId>
</Error>"""

S3_DELETE_BUCKET_WITH_ITEMS_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<Error><Code>BucketNotEmpty</Code>
<Message>The bucket you tried to delete is not empty</Message>
<BucketName>{{ bucket.name }}</BucketName>
<RequestId>asdfasdfsdafds</RequestId>
<HostId>sdfgdsfgdsfgdfsdsfgdfs</HostId>
</Error>"""

S3_DELETE_OBJECT_SUCCESS = """<DeleteObjectResponse xmlns="http://s3.amazonaws.com/doc/2006-03-01">
  <DeleteObjectResponse>
    <Code>200</Code>
    <Description>OK</Description>
  </DeleteObjectResponse>
</DeleteObjectResponse>"""

S3_OBJECT_RESPONSE = """<PutObjectResponse xmlns="http://s3.amazonaws.com/doc/2006-03-01">
      <PutObjectResponse>
        <ETag>&quot;asdlfkdalsjfsalfkjsadlfjsdjkk&quot;</ETag>
        <LastModified>2006-03-01T12:00:00.183Z</LastModified>
      </PutObjectResponse>
    </PutObjectResponse>"""