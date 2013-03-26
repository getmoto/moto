from urlparse import parse_qs

from jinja2 import Template

from .models import s3_backend
from moto.core.utils import headers_to_dict
from .utils import bucket_name_from_hostname


def all_buckets():
    # No bucket specified. Listing all buckets
    all_buckets = s3_backend.get_all_buckets()
    template = Template(S3_ALL_BUCKETS)
    return template.render(buckets=all_buckets)


def bucket_response(uri, method, body, headers):
    hostname = uri.hostname
    querystring = parse_qs(uri.query)

    bucket_name = bucket_name_from_hostname(hostname)
    if not bucket_name:
        # If no bucket specified, list all buckets
        return all_buckets()

    if method == 'GET':
        bucket = s3_backend.get_bucket(bucket_name)
        if bucket:
            prefix = querystring.get('prefix', [None])[0]
            result_keys, result_folders = s3_backend.prefix_query(bucket, prefix)
            template = Template(S3_BUCKET_GET_RESPONSE)
            return template.render(
                bucket=bucket,
                prefix=prefix,
                result_keys=result_keys,
                result_folders=result_folders
            )
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
        raise NotImplementedError("Method {} has not been impelemented in the S3 backend yet".format(method))


def key_response(uri_info, method, body, headers):

    key_name = uri_info.path.lstrip('/')
    hostname = uri_info.hostname
    headers = headers_to_dict(headers)

    bucket_name = bucket_name_from_hostname(hostname)

    if method == 'GET':
        key = s3_backend.get_key(bucket_name, key_name)
        if key:
            return key.value
        else:
            return "", dict(status=404)
    if method == 'PUT':
        if 'x-amz-copy-source' in headers:
            # Copy key
            src_bucket, src_key = headers.get("x-amz-copy-source").split("/")
            s3_backend.copy_key(src_bucket, src_key, bucket_name, key_name)
            template = Template(S3_OBJECT_COPY_RESPONSE)
            return template.render(key=src_key)
        if body is not None:
            key = s3_backend.get_key(bucket_name, key_name)
            if not key or body:
                # We want to write the key in once of two circumstances.
                # - The key does not currently exist.
                # - The key already exists, but body is a truthy value.
                # This allows us to write empty strings to keys for the first
                # write, but not subsequent. This is because HTTPretty sends
                # an empty string on connection close. This is a temporary fix
                # while HTTPretty gets fixed.
                new_key = s3_backend.set_key(bucket_name, key_name, body)
                template = Template(S3_OBJECT_RESPONSE)
                return template.render(key=new_key), dict(etag=new_key.etag)
        key = s3_backend.get_key(bucket_name, key_name)
        if key:
            return "", dict(etag=key.etag)
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
    elif method == 'POST':
        if body == '' and uri_info.query == 'uploads':
            multipart = s3_backend.initiate_multipart(bucket_name, key_name)
            template = Template(S3_MULTIPART_RESPONSE)
            response = template.render(
                bucket_name=bucket_name,
                key_name=key_name,
                multipart_id=multipart.id,
            )
            print response
            return response, dict()
        else:
            import pdb; pdb.set_trace()
            raise NotImplementedError("POST is only allowed for multipart uploads")
    else:
        raise NotImplementedError("Method {} has not been impelemented in the S3 backend yet".format(method))


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

S3_BUCKET_GET_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Name>{{ bucket.name }}</Name>
  <Prefix>{{ prefix }}</Prefix>
  <MaxKeys>1000</MaxKeys>
  <Delimiter>/</Delimiter>
  <IsTruncated>false</IsTruncated>
  {% for key in result_keys %}
    <Contents>
      <Key>{{ key.name }}</Key>
      <LastModified>2006-01-01T12:00:00.000Z</LastModified>
      <ETag>{{ key.etag }}</ETag>
      <Size>{{ key.size }}</Size>
      <StorageClass>STANDARD</StorageClass>
      <Owner>
        <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
        <DisplayName>webfile</DisplayName>
      </Owner>
      <StorageClass>STANDARD</StorageClass>
    </Contents>
  {% endfor %}
  {% for folder in result_folders %}
    <CommonPrefixes>
      <Prefix>{{ folder }}</Prefix>
    </CommonPrefixes>
  {% endfor %}
  </ListBucketResult>"""

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
        <ETag>{{ key.etag }}</ETag>
        <LastModified>2006-03-01T12:00:00.183Z</LastModified>
      </PutObjectResponse>
    </PutObjectResponse>"""

S3_OBJECT_COPY_RESPONSE = """<CopyObjectResponse xmlns="http://doc.s3.amazonaws.com/2006-03-01">
  <CopyObjectResponse>
    <ETag>{{ key.etag }}</ETag>
    <LastModified>2008-02-18T13:54:10.183Z</LastModified>
  </CopyObjectResponse>
</CopyObjectResponse>"""

S3_MULTIPART_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<InitiateMultipartUploadResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Bucket>{{ bucket_name }}</Bucket>
  <Key>{{ key_name }}</Key>
  <UploadId>{{ upload_id }}</UploadId>
</InitiateMultipartUploadResult>"""

S3_MULTIPART_COMPLETE_RESPONSE = """
"""

S3_MULTIPART_ERROR_RESPONSE = """
"""
