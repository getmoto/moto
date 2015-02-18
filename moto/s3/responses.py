from __future__ import unicode_literals

import re

import six
from six.moves.urllib.parse import parse_qs, urlparse, quote, unquote

from moto.core.responses import _TemplateEnvironmentMixin

from .exceptions import BucketAlreadyExists, S3ClientError, InvalidPartOrder
from .models import s3_backend
from .utils import bucket_name_from_url, metadata_from_headers
from xml.dom import minidom

REGION_URL_REGEX = r'\.s3-(.+?)\.amazonaws\.com'
DEFAULT_REGION_NAME = 'us-east-1'


def parse_key_name(pth):
    if pth[0] == '/':
        pth = pth[1:]
    return unquote(pth).decode('utf-8')


class ResponseObject(_TemplateEnvironmentMixin):
    def __init__(self, backend, bucket_name_from_url, parse_key_name):
        self.backend = backend
        self.bucket_name_from_url = bucket_name_from_url
        self.parse_key_name = parse_key_name

    def all_buckets(self):
        # No bucket specified. Listing all buckets
        all_buckets = self.backend.get_all_buckets()
        template = self.response_template(S3_ALL_BUCKETS)
        return template.render(buckets=all_buckets)

    def bucket_response(self, request, full_url, headers):
        try:
            response = self._bucket_response(request, full_url, headers)
        except S3ClientError as s3error:
            response = s3error.code, headers, s3error.description

        if isinstance(response, six.string_types):
            return 200, headers, response.encode("utf-8")
        else:
            status_code, headers, response_content = response
            return status_code, headers, response_content.encode("utf-8")

    def _bucket_response(self, request, full_url, headers):
        parsed_url = urlparse(full_url)
        querystring = parse_qs(parsed_url.query, keep_blank_values=True)
        method = request.method
        region_name = DEFAULT_REGION_NAME
        region_match = re.search(REGION_URL_REGEX, full_url)
        if region_match:
            region_name = region_match.groups()[0]

        bucket_name = self.bucket_name_from_url(full_url)
        if not bucket_name:
            # If no bucket specified, list all buckets
            return self.all_buckets()

        if method == 'HEAD':
            return self._bucket_response_head(bucket_name, headers)
        elif method == 'GET':
            return self._bucket_response_get(bucket_name, querystring, headers)
        elif method == 'PUT':
            return self._bucket_response_put(request, region_name, bucket_name, querystring, headers)
        elif method == 'DELETE':
            return self._bucket_response_delete(bucket_name, headers)
        elif method == 'POST':
            return self._bucket_response_post(request, bucket_name, headers)
        else:
            raise NotImplementedError("Method {0} has not been impelemented in the S3 backend yet".format(method))

    def _bucket_response_head(self, bucket_name, headers):
        self.backend.get_bucket(bucket_name)
        return 200, headers, ""

    def _bucket_response_get(self, bucket_name, querystring, headers):
        if 'uploads' in querystring:
            for unsup in ('delimiter', 'max-uploads'):
                if unsup in querystring:
                    raise NotImplementedError("Listing multipart uploads with {} has not been implemented yet.".format(unsup))
            multiparts = list(self.backend.get_all_multiparts(bucket_name).values())
            if 'prefix' in querystring:
                prefix = querystring.get('prefix', [None])[0]
                multiparts = [upload for upload in multiparts if upload.key_name.startswith(prefix)]
            template = self.response_template(S3_ALL_MULTIPARTS)
            return 200, headers, template.render(
                bucket_name=bucket_name,
                uploads=multiparts)
        elif 'location' in querystring:
            bucket = self.backend.get_bucket(bucket_name)
            template = self.response_template(S3_BUCKET_LOCATION)
            return 200, headers, template.render(location=bucket.location)
        elif 'versioning' in querystring:
            versioning = self.backend.get_bucket_versioning(bucket_name)
            template = self.response_template(S3_BUCKET_GET_VERSIONING)
            return 200, headers, template.render(status=versioning)
        elif 'versions' in querystring:
            delimiter = querystring.get('delimiter', [None])[0]
            encoding_type = querystring.get('encoding-type', [None])[0]
            key_marker = querystring.get('key-marker', [None])[0]
            max_keys = querystring.get('max-keys', [None])[0]
            prefix = querystring.get('prefix', [None])[0]
            version_id_marker = querystring.get('version-id-marker', [None])[0]

            bucket = self.backend.get_bucket(bucket_name)
            versions = self.backend.get_bucket_versions(
                bucket_name,
                delimiter=delimiter,
                encoding_type=encoding_type,
                key_marker=key_marker,
                max_keys=max_keys,
                version_id_marker=version_id_marker
            )
            template = self.response_template(S3_BUCKET_GET_VERSIONS)
            return 200, headers, template.render(
                key_list=versions,
                bucket=bucket,
                prefix='',
                max_keys='',
                delimiter='',
                is_truncated='false',
            )

        bucket = self.backend.get_bucket(bucket_name)
        prefix = querystring.get('prefix', [None])[0]
        delimiter = querystring.get('delimiter', [None])[0]
        encoding_type = querystring.get('encoding-type', [None])[0]
        result_keys, result_folders = self.backend.prefix_query(bucket, prefix, delimiter)
        if encoding_type == 'url':
            result_keys = [k.copy(quote(k.name.encode('utf-8'))) for k in result_keys]
            result_folders = [quote(f.encode('utf-8')) for f in result_folders]
        template = self.response_template(S3_BUCKET_GET_RESPONSE)
        return 200, headers, template.render(
            bucket=bucket,
            prefix=prefix,
            delimiter=delimiter,
            result_keys=result_keys,
            result_folders=result_folders,
            encoding_type=encoding_type
        ).encode('utf-8')

    def _bucket_response_put(self, request, region_name, bucket_name, querystring, headers):
        if 'versioning' in querystring:
            ver = re.search('<Status>([A-Za-z]+)</Status>', request.body.decode('utf-8'))
            if ver:
                self.backend.set_bucket_versioning(bucket_name, ver.group(1))
                template = self.response_template(S3_BUCKET_VERSIONING)
                return template.render(bucket_versioning_status=ver.group(1))
            else:
                return 404, headers, ""
        else:
            try:
                new_bucket = self.backend.create_bucket(bucket_name, region_name)
            except BucketAlreadyExists:
                if region_name == DEFAULT_REGION_NAME:
                    # us-east-1 has different behavior
                    new_bucket = self.backend.get_bucket(bucket_name)
                else:
                    raise
            template = self.response_template(S3_BUCKET_CREATE_RESPONSE)
            return 200, headers, template.render(bucket=new_bucket)

    def _bucket_response_delete(self, bucket_name, headers):
        removed_bucket = self.backend.delete_bucket(bucket_name)

        if removed_bucket:
            # Bucket exists
            template = self.response_template(S3_DELETE_BUCKET_SUCCESS)
            return 204, headers, template.render(bucket=removed_bucket)
        else:
            # Tried to delete a bucket that still has keys
            template = self.response_template(S3_DELETE_BUCKET_WITH_ITEMS_ERROR)
            return 409, headers, template.render(bucket=removed_bucket)

    def _bucket_response_post(self, request, bucket_name, headers):
        if request.path == u'/?delete':
            return self._bucket_response_delete_keys(request, bucket_name, headers)

        # POST to bucket-url should create file from form
        if hasattr(request, 'form'):
            # Not HTTPretty
            form = request.form
        else:
            # HTTPretty, build new form object
            form = {}
            for kv in request.body.decode('utf-8').split('&'):
                k, v = kv.split('=')
                form[k] = v

        key = form['key']
        if 'file' in form:
            f = form['file']
        else:
            f = request.files['file'].stream.read()

        new_key = self.backend.set_key(bucket_name, key, f)

        # Metadata
        metadata = metadata_from_headers(form)
        new_key.set_metadata(metadata)

        return 200, headers, ""

    def _bucket_response_delete_keys(self, request, bucket_name, headers):
        template = self.response_template(S3_DELETE_KEYS_RESPONSE)

        keys = minidom.parseString(request.body.decode('utf-8')).getElementsByTagName('Key')
        deleted_names = []
        error_names = []

        for k in keys:
            try:
                key_name = k.firstChild.nodeValue
                self.backend.delete_key(bucket_name, key_name)
                deleted_names.append(key_name)
            except KeyError:
                error_names.append(key_name)

        return 200, headers, template.render(deleted=deleted_names, delete_errors=error_names)

    def _handle_range_header(self, request, headers, response_content):
        length = len(response_content)
        last = length - 1
        _, rspec = request.headers.get('range').split('=')
        if ',' in rspec:
            raise NotImplementedError(
                "Multiple range specifiers not supported")
        toint = lambda i: int(i) if i else None
        begin, end = map(toint, rspec.split('-'))
        if begin is not None:  # byte range
            end = last if end is None else end
        elif end is not None:  # suffix byte range
            begin = length - end
            end = last
        else:
            return 400, headers, ""
        if begin < 0 or end > length or begin > min(end, last):
            return 416, headers, ""
        headers['content-range'] = "bytes {0}-{1}/{2}".format(
            begin, end, length)
        return 206, headers, response_content[begin:end + 1]

    def key_response(self, request, full_url, headers):
        try:
            response = self._key_response(request, full_url, headers)
        except S3ClientError as s3error:
            response = s3error.code, headers, s3error.description

        if isinstance(response, six.string_types):
            status_code = 200
            response_content = response
        else:
            status_code, headers, response_content = response

        if status_code == 200 and 'range' in request.headers:
            return self._handle_range_header(request, headers, response_content)
        return status_code, headers, response_content

    def _key_response(self, request, full_url, headers):
        parsed_url = urlparse(full_url.encode('utf-8'))
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
            return self._key_response_get(bucket_name, query, key_name, headers)
        elif method == 'PUT':
            return self._key_response_put(request, parsed_url, body, bucket_name, query, key_name, headers)
        elif method == 'HEAD':
            return self._key_response_head(bucket_name, key_name, headers)
        elif method == 'DELETE':
            return self._key_response_delete(bucket_name, query, key_name, headers)
        elif method == 'POST':
            return self._key_response_post(request, body, parsed_url, bucket_name, query, key_name, headers)
        else:
            raise NotImplementedError("Method {0} has not been impelemented in the S3 backend yet".format(method))

    def _key_response_get(self, bucket_name, query, key_name, headers):
        if 'uploadId' in query:
            upload_id = query['uploadId'][0]
            parts = self.backend.list_multipart(bucket_name, upload_id)
            template = self.response_template(S3_MULTIPART_LIST_RESPONSE)
            return 200, headers, template.render(
                bucket_name=bucket_name,
                key_name=key_name,
                upload_id=upload_id,
                count=len(parts),
                parts=parts
            )
        version_id = query.get('versionId', [None])[0]
        key = self.backend.get_key(
            bucket_name, key_name, version_id=version_id)
        if key:
            headers.update(key.metadata)
            return 200, headers, key.value
        else:
            return 404, headers, ""

    def _key_response_put(self, request, parsed_url, body, bucket_name, query, key_name, headers):
        if 'uploadId' in query and 'partNumber' in query:
            upload_id = query['uploadId'][0]
            part_number = int(query['partNumber'][0])
            if 'x-amz-copy-source' in request.headers:
                src = request.headers.get("x-amz-copy-source")
                src_bucket, src_key = src.split("/", 1)
                key = self.backend.copy_part(
                    bucket_name, upload_id, part_number, src_bucket,
                    src_key)
                template = self.response_template(S3_MULTIPART_UPLOAD_RESPONSE)
                response = template.render(part=key)
            else:
                key = self.backend.set_part(
                    bucket_name, upload_id, part_number, body)
                response = ""
            headers.update(key.response_dict)
            return 200, headers, response

        storage_class = request.headers.get('x-amz-storage-class', 'STANDARD')

        if parsed_url.query == 'acl':
            # We don't implement ACL yet, so just return
            return 200, headers, ""

        if 'x-amz-copy-source' in request.headers:
            # Copy key
            src_bucket, src_key = request.headers.get("x-amz-copy-source").split("/", 1)
            self.backend.copy_key(src_bucket, src_key, bucket_name, key_name,
                                  storage=storage_class)
            mdirective = request.headers.get('x-amz-metadata-directive')
            if mdirective is not None and mdirective == 'REPLACE':
                new_key = self.backend.get_key(bucket_name, key_name)
                metadata = metadata_from_headers(request.headers)
                new_key.set_metadata(metadata, replace=True)
            template = self.response_template(S3_OBJECT_COPY_RESPONSE)
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
            new_key = self.backend.set_key(bucket_name, key_name, body,
                                           storage=storage_class)
            request.streaming = True
            metadata = metadata_from_headers(request.headers)
            new_key.set_metadata(metadata)

        template = self.response_template(S3_OBJECT_RESPONSE)
        headers.update(new_key.response_dict)
        return 200, headers, template.render(key=new_key)

    def _key_response_head(self, bucket_name, key_name, headers):
        key = self.backend.get_key(bucket_name, key_name)
        if key:
            headers.update(key.metadata)
            headers.update(key.response_dict)
            return 200, headers, key.value
        else:
            return 404, headers, ""

    def _key_response_delete(self, bucket_name, query, key_name, headers):
        if 'uploadId' in query:
            upload_id = query['uploadId'][0]
            self.backend.cancel_multipart(bucket_name, upload_id)
            return 204, headers, ""
        removed_key = self.backend.delete_key(bucket_name, key_name)
        template = self.response_template(S3_DELETE_OBJECT_SUCCESS)
        return 204, headers, template.render(bucket=removed_key)

    def _complete_multipart_body(self, body):
        ps = minidom.parseString(body).getElementsByTagName('Part')
        prev = 0
        for p in ps:
            pn = int(p.getElementsByTagName('PartNumber')[0].firstChild.wholeText)
            if pn <= prev:
                raise InvalidPartOrder()
            yield (pn, p.getElementsByTagName('ETag')[0].firstChild.wholeText)

    def _key_response_post(self, request, body, parsed_url, bucket_name, query, key_name, headers):
        if body == b'' and parsed_url.query == 'uploads':
            metadata = metadata_from_headers(request.headers)
            multipart = self.backend.initiate_multipart(bucket_name, key_name, metadata)

            template = self.response_template(S3_MULTIPART_INITIATE_RESPONSE)
            response = template.render(
                bucket_name=bucket_name,
                key_name=key_name,
                upload_id=multipart.id,
            )
            return 200, headers, response

        if 'uploadId' in query:
            body = self._complete_multipart_body(body)
            upload_id = query['uploadId'][0]
            key = self.backend.complete_multipart(bucket_name, upload_id, body)
            template = self.response_template(S3_MULTIPART_COMPLETE_RESPONSE)
            return template.render(
                bucket_name=bucket_name,
                key_name=key.name,
                etag=key.etag,
            )
        elif parsed_url.query == 'restore':
            es = minidom.parseString(body).getElementsByTagName('Days')
            days = es[0].childNodes[0].wholeText
            key = self.backend.get_key(bucket_name, key_name)
            r = 202
            if key.expiry_date is not None:
                r = 200
            key.restore(int(days))
            return r, headers, ""
        else:
            raise NotImplementedError("Method POST had only been implemented for multipart uploads and restore operations, so far")

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
      <StorageClass>{{ key.storage_class }}</StorageClass>
      <Owner>
        <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
        <DisplayName>webfile</DisplayName>
      </Owner>
    </Contents>
  {% endfor %}
  {% if delimiter %}
    {% for folder in result_folders %}
      <CommonPrefixes>
        <Prefix>{{ folder }}</Prefix>
      </CommonPrefixes>
    {% endfor %}
  {% endif %}
  {% if encoding_type %}
    <Encoding-Type>{{ encoding_type }}</Encoding-Type>
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

S3_DELETE_BUCKET_WITH_ITEMS_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<Error><Code>BucketNotEmpty</Code>
<Message>The bucket you tried to delete is not empty</Message>
<BucketName>{{ bucket.name }}</BucketName>
<RequestId>asdfasdfsdafds</RequestId>
<HostId>sdfgdsfgdsfgdfsdsfgdfs</HostId>
</Error>"""

S3_BUCKET_LOCATION = """<?xml version="1.0" encoding="UTF-8"?>
<LocationConstraint xmlns="http://s3.amazonaws.com/doc/2006-03-01/">{{ location }}</LocationConstraint>"""

S3_BUCKET_VERSIONING = """
<?xml version="1.0" encoding="UTF-8"?>
<VersioningConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Status>{{ bucket_versioning_status }}</Status>
</VersioningConfiguration>
"""

S3_BUCKET_GET_VERSIONING = """
<?xml version="1.0" encoding="UTF-8"?>
{% if status is none %}
    <VersioningConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/"/>
{% else %}
    <VersioningConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Status>{{ status }}</Status>
    </VersioningConfiguration>
{% endif %}
"""

S3_BUCKET_GET_VERSIONS = """<?xml version="1.0" encoding="UTF-8"?>
<ListVersionsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01">
    <Name>{{ bucket.name }}</Name>
    <Prefix>{{ prefix }}</Prefix>
    <KeyMarker>{{ key_marker }}</KeyMarker>
    <MaxKeys>{{ max_keys }}</MaxKeys>
    <IsTruncated>{{ is_truncated }}</IsTruncated>
    {% for key in key_list %}
    <Version>
        <Key>{{ key.name }}</Key>
        <VersionId>{{ key._version_id }}</VersionId>
        <IsLatest>false</IsLatest>
        <LastModified>{{ key.last_modified_ISO8601 }}</LastModified>
        <ETag>{{ key.etag }}</ETag>
        <Size>{{ key.size }}</Size>
        <StorageClass>{{ key.storage_class }}</StorageClass>
        <Owner>
            <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
            <DisplayName>webfile</DisplayName>
        </Owner>
    </Version>
    {% endfor %}
</ListVersionsResult>
"""

S3_DELETE_KEYS_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<DeleteResult xmlns="http://s3.amazonaws.com/doc/2006-03-01">
{% for k in deleted %}
<Deleted>
<Key>{{k}}</Key>
</Deleted>
{% endfor %}
{% for k in delete_errors %}
<Error>
<Key>{{k}}</Key>
</Error>
{% endfor %}
</DeleteResult>"""

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

S3_ALL_MULTIPARTS = """<?xml version="1.0" encoding="UTF-8"?>
<ListMultipartUploadsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Bucket>{{ bucket_name }}</Bucket>
  <KeyMarker></KeyMarker>
  <UploadIdMarker></UploadIdMarker>
  <MaxUploads>1000</MaxUploads>
  <IsTruncated>False</IsTruncated>
  {% for upload in uploads %}
  <Upload>
    <Key>{{ upload.key_name }}</Key>
    <UploadId>{{ upload.id }}</UploadId>
    <Initiator>
      <ID>arn:aws:iam::111122223333:user/user1-11111a31-17b5-4fb7-9df5-b111111f13de</ID>
      <DisplayName>user1-11111a31-17b5-4fb7-9df5-b111111f13de</DisplayName>
    </Initiator>
    <Owner>
      <ID>75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a</ID>
      <DisplayName>OwnerDisplayName</DisplayName>
    </Owner>
    <StorageClass>STANDARD</StorageClass>
    <Initiated>2010-11-10T20:48:33.000Z</Initiated>
  </Upload>
  {% endfor %}
</ListMultipartUploadsResult>
"""
