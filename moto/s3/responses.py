from urlparse import parse_qs, urlparse
import re

from jinja2 import Template

from .models import s3_backend
from .utils import bucket_name_from_url


def parse_key_name(pth):
    return pth.lstrip("/")


class ResponseObject(object):
    def __init__(self, backend, bucket_name_from_url, parse_key_name):
        self.backend = backend
        self.bucket_name_from_url = bucket_name_from_url
        self.parse_key_name = parse_key_name

    def all_buckets(self):
        # No bucket specified. Listing all buckets
        all_buckets = self.backend.get_all_buckets()
        template = Template(S3_ALL_BUCKETS)
        return template.render(buckets=all_buckets)

    def bucket_response(self, request, full_url, headers):
        response = self._bucket_response(request, full_url, headers)
        if isinstance(response, basestring):
            return 200, headers, response

        else:
            status_code, headers, response_content = response
            return status_code, headers, response_content

    def _bucket_response(self, request, full_url, headers):
        parsed_url = urlparse(full_url)
        querystring = parse_qs(parsed_url.query)
        method = request.method

        bucket_name = self.bucket_name_from_url(full_url)
        if not bucket_name:
            # If no bucket specified, list all buckets
            return self.all_buckets()

        if method == 'GET':
            bucket = self.backend.get_bucket(bucket_name)
            if bucket:
                prefix = querystring.get('prefix', [None])[0]
                delimiter = querystring.get('delimiter', [None])[0]
                result_keys, result_folders = self.backend.prefix_query(bucket, prefix, delimiter)
                template = Template(S3_BUCKET_GET_RESPONSE)
                return template.render(
                    bucket=bucket,
                    prefix=prefix,
                    delimiter=delimiter,
                    result_keys=result_keys,
                    result_folders=result_folders
                )
            else:
                return 404, headers, ""
        elif method == 'PUT':
            new_bucket = self.backend.create_bucket(bucket_name)
            template = Template(S3_BUCKET_CREATE_RESPONSE)
            return template.render(bucket=new_bucket)
        elif method == 'DELETE':
            removed_bucket = self.backend.delete_bucket(bucket_name)
            if removed_bucket is None:
                # Non-existant bucket
                template = Template(S3_DELETE_NON_EXISTING_BUCKET)
                return 404, headers, template.render(bucket_name=bucket_name)
            elif removed_bucket:
                # Bucket exists
                template = Template(S3_DELETE_BUCKET_SUCCESS)
                return 204, headers, template.render(bucket=removed_bucket)
            else:
                # Tried to delete a bucket that still has keys
                template = Template(S3_DELETE_BUCKET_WITH_ITEMS_ERROR)
                return 409, headers, template.render(bucket=removed_bucket)
        elif method == 'POST':
            #POST to bucket-url should create file from form
            if hasattr(request, 'form'):
                #Not HTTPretty
                form = request.form
            else:
                #HTTPretty, build new form object
                form = {}
                for kv in request.body.split('&'):
                    k, v = kv.split('=')
                    form[k] = v

            key = form['key']
            f = form['file']

            new_key = self.backend.set_key(bucket_name, key, f)

            #Metadata
            meta_regex = re.compile('^x-amz-meta-([a-zA-Z0-9\-_]+)$', flags=re.IGNORECASE)

            for form_id in form:
                result = meta_regex.match(form_id)
                if result:
                    meta_key = result.group(0).lower()
                    metadata = form[form_id]
                    new_key.set_metadata(meta_key, metadata)
            return 200, headers, ""
        else:
            raise NotImplementedError("Method {0} has not been impelemented in the S3 backend yet".format(method))

    def key_response(self, request, full_url, headers):
        response = self._key_response(request, full_url, headers)
        if isinstance(response, basestring):
            return 200, headers, response
        else:
            status_code, headers, response_content = response
            return status_code, headers, response_content

    def _key_response(self, request, full_url, headers):
        parsed_url = urlparse(full_url)
        query = parse_qs(parsed_url.query)
        method = request.method

        key_name = self.parse_key_name(parsed_url.path)

        bucket_name = self.bucket_name_from_url(full_url)

        if hasattr(request, 'body'):
            # Boto
            body = request.body
        else:
            # Flask server
            body = request.data

        if method == 'GET':
            if 'uploadId' in query:
                upload_id = query['uploadId'][0]
                parts = self.backend.list_multipart(bucket_name, upload_id)
                template = Template(S3_MULTIPART_LIST_RESPONSE)
                return 200, headers, template.render(
                    bucket_name=bucket_name,
                    key_name=key_name,
                    upload_id=upload_id,
                    count=len(parts),
                    parts=parts
                    )
            key = self.backend.get_key(bucket_name, key_name)
            if key:
                headers.update(key.metadata)
                return 200, headers, key.value
            else:
                return 404, headers, ""
        if method == 'PUT':
            if 'uploadId' in query and 'partNumber' in query and body:
                upload_id = query['uploadId'][0]
                part_number = int(query['partNumber'][0])
                key = self.backend.set_part(bucket_name, upload_id, part_number, body)
                template = Template(S3_MULTIPART_UPLOAD_RESPONSE)
                headers.update(key.response_dict)
                return 200, headers, template.render(part=key)

            if 'x-amz-copy-source' in request.headers:
                # Copy key
                src_bucket, src_key = request.headers.get("x-amz-copy-source").split("/", 1)
                self.backend.copy_key(src_bucket, src_key, bucket_name, key_name)
                template = Template(S3_OBJECT_COPY_RESPONSE)
                return template.render(key=src_key)
            streaming_request = hasattr(request, 'streaming') and request.streaming
            closing_connection = headers.get('connection') == 'close'
            if closing_connection and streaming_request:
                # Closing the connection of a streaming request. No more data
                new_key = self.backend.get_key(bucket_name, key_name)
            elif streaming_request:
                # Streaming request, more data
                new_key = self.backend.append_to_key(bucket_name, key_name, body)
            else:
                # Initial data
                new_key = self.backend.set_key(bucket_name, key_name, body)
                request.streaming = True

                #Metadata
                meta_regex = re.compile('^x-amz-meta-([a-zA-Z0-9\-_]+)$', flags=re.IGNORECASE)
                for header in request.headers:
                    if isinstance(header, basestring):
                        result = meta_regex.match(header)
                        if result:
                            meta_key = result.group(0).lower()
                            metadata = request.headers[header]
                            new_key.set_metadata(meta_key, metadata)
            template = Template(S3_OBJECT_RESPONSE)
            headers.update(new_key.response_dict)
            return 200, headers, template.render(key=new_key)
        elif method == 'HEAD':
            key = self.backend.get_key(bucket_name, key_name)
            if key:
                headers.update(key.metadata)
                headers.update(key.response_dict)
                return 200, headers, ""
            else:
                return 404, headers, ""
        elif method == 'DELETE':
            if 'uploadId' in query:
                upload_id = query['uploadId'][0]
                self.backend.cancel_multipart(bucket_name, upload_id)
                return 204, headers, ""
            removed_key = self.backend.delete_key(bucket_name, key_name)
            template = Template(S3_DELETE_OBJECT_SUCCESS)
            return 204, headers, template.render(bucket=removed_key)
        elif method == 'POST':
            if body == '' and parsed_url.query == 'uploads':
                multipart = self.backend.initiate_multipart(bucket_name, key_name)
                template = Template(S3_MULTIPART_INITIATE_RESPONSE)
                response = template.render(
                    bucket_name=bucket_name,
                    key_name=key_name,
                    upload_id=multipart.id,
                )
                return 200, headers, response

            if 'uploadId' in query:
                upload_id = query['uploadId'][0]
                key = self.backend.complete_multipart(bucket_name, upload_id)

                if key is not None:
                    template = Template(S3_MULTIPART_COMPLETE_RESPONSE)
                    return template.render(
                        bucket_name=bucket_name,
                        key_name=key.name,
                        etag=key.etag,
                    )
                template = Template(S3_MULTIPART_COMPLETE_TOO_SMALL_ERROR)
                return 400, headers, template.render()
            else:
                raise NotImplementedError("Method POST had only been implemented for multipart uploads so far")
        else:
            raise NotImplementedError("Method {0} has not been impelemented in the S3 backend yet".format(method))

S3ResponseInstance = ResponseObject(s3_backend, bucket_name_from_url, parse_key_name)

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
  <Delimiter>{{ delimiter }}</Delimiter>
  <IsTruncated>false</IsTruncated>
  {% for key in result_keys %}
    <Contents>
      <Key>{{ key.name }}</Key>
      <LastModified>{{ key.last_modified_ISO8601 }}</LastModified>
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
  {% if delimiter %}
    {% for folder in result_folders %}
      <CommonPrefixes>
        <Prefix>{{ folder }}</Prefix>
      </CommonPrefixes>
    {% endfor %}
  {% endif %}
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
        <LastModified>{{ key.last_modified_ISO8601 }}</LastModified>
      </PutObjectResponse>
    </PutObjectResponse>"""

S3_OBJECT_COPY_RESPONSE = """<CopyObjectResponse xmlns="http://doc.s3.amazonaws.com/2006-03-01">
  <CopyObjectResponse>
    <ETag>{{ key.etag }}</ETag>
    <LastModified>{{ key.last_modified_ISO8601 }}</LastModified>
  </CopyObjectResponse>
</CopyObjectResponse>"""

S3_MULTIPART_INITIATE_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<InitiateMultipartUploadResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Bucket>{{ bucket_name }}</Bucket>
  <Key>{{ key_name }}</Key>
  <UploadId>{{ upload_id }}</UploadId>
</InitiateMultipartUploadResult>"""

S3_MULTIPART_UPLOAD_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<CopyPartResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <LastModified>{{ part.last_modified_ISO8601 }}</LastModified>
  <ETag>{{ part.etag }}</ETag>
</CopyPartResult>"""

S3_MULTIPART_LIST_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<ListPartsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Bucket>{{ bucket_name }}</Bucket>
  <Key>{{ key_name }}</Key>
  <UploadId>{{ upload_id }}</UploadId>
  <StorageClass>STANDARD</StorageClass>
  <Initiator>
    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
    <DisplayName>webfile</DisplayName>
  </Initiator>
  <Owner>
    <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
    <DisplayName>webfile</DisplayName>
  </Owner>
  <StorageClass>STANDARD</StorageClass>
  <PartNumberMarker>1</PartNumberMarker>
  <NextPartNumberMarker>{{ count }} </NextPartNumberMarker>
  <MaxParts>{{ count }}</MaxParts>
  <IsTruncated>false</IsTruncated>
  {% for part in parts %}
  <Part>
    <PartNumber>{{ part.name }}</PartNumber>
    <LastModified>{{ part.last_modified_ISO8601 }}</LastModified>
    <ETag>{{ part.etag }}</ETag>
    <Size>{{ part.size }}</Size>
  </Part>
  {% endfor %}
</ListPartsResult>"""

S3_MULTIPART_COMPLETE_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<CompleteMultipartUploadResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Location>http://{{ bucket_name }}.s3.amazonaws.com/{{ key_name }}</Location>
  <Bucket>{{ bucket_name }}</Bucket>
  <Key>{{ key_name }}</Key>
  <ETag>{{ etag }}</ETag>
</CompleteMultipartUploadResult>
"""

S3_MULTIPART_COMPLETE_TOO_SMALL_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<Error>
  <Code>EntityTooSmall</Code>
  <Message>Your proposed upload is smaller than the minimum allowed object size.</Message>
  <RequestId>asdfasdfsdafds</RequestId>
  <HostId>sdfgdsfgdsfgdfsdsfgdfs</HostId>
</Error>"""
