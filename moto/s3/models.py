from __future__ import unicode_literals
import os
import base64
import datetime
import hashlib
import copy
import itertools
import codecs
import six

from bisect import insort
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, rfc_1123_datetime
from .exceptions import BucketAlreadyExists, MissingBucket, InvalidPart, EntityTooSmall, MissingKey
from .utils import clean_key_name, _VersionedKeyStore

UPLOAD_ID_BYTES = 43
UPLOAD_PART_MIN_SIZE = 5242880


class FakeDeleteMarker(BaseModel):

    def __init__(self, key):
        self.key = key
        self._version_id = key.version_id + 1

    @property
    def version_id(self):
        return self._version_id


class FakeKey(BaseModel):

    def __init__(self, name, value, storage="STANDARD", etag=None, is_versioned=False, version_id=0):
        self.name = name
        self.value = value
        self.last_modified = datetime.datetime.utcnow()
        self.acl = get_canned_acl('private')
        self.website_redirect_location = None
        self._storage_class = storage if storage else "STANDARD"
        self._metadata = {}
        self._expiry = None
        self._etag = etag
        self._version_id = version_id
        self._is_versioned = is_versioned
        self._tagging = FakeTagging()

    @property
    def version_id(self):
        return self._version_id

    def copy(self, new_name=None):
        r = copy.deepcopy(self)
        if new_name is not None:
            r.name = new_name
        return r

    def set_metadata(self, metadata, replace=False):
        if replace:
            self._metadata = {}
        self._metadata.update(metadata)

    def set_tagging(self, tagging):
        self._tagging = tagging

    def set_storage_class(self, storage_class):
        self._storage_class = storage_class

    def set_acl(self, acl):
        self.acl = acl

    def append_to_value(self, value):
        self.value += value
        self.last_modified = datetime.datetime.utcnow()
        self._etag = None  # must recalculate etag
        if self._is_versioned:
            self._version_id += 1
        else:
            self._is_versioned = 0

    def restore(self, days):
        self._expiry = datetime.datetime.utcnow() + datetime.timedelta(days)

    def increment_version(self):
        self._version_id += 1

    @property
    def etag(self):
        if self._etag is None:
            value_md5 = hashlib.md5()
            if isinstance(self.value, six.text_type):
                value = self.value.encode("utf-8")
            else:
                value = self.value
            value_md5.update(value)
            self._etag = value_md5.hexdigest()
        return '"{0}"'.format(self._etag)

    @property
    def last_modified_ISO8601(self):
        return iso_8601_datetime_with_milliseconds(self.last_modified)

    @property
    def last_modified_RFC1123(self):
        # Different datetime formats depending on how the key is obtained
        # https://github.com/boto/boto/issues/466
        return rfc_1123_datetime(self.last_modified)

    @property
    def metadata(self):
        return self._metadata

    @property
    def tagging(self):
        return self._tagging

    @property
    def response_dict(self):
        res = {
            'ETag': self.etag,
            'last-modified': self.last_modified_RFC1123,
            'content-length': str(len(self.value)),
        }
        if self._storage_class != 'STANDARD':
            res['x-amz-storage-class'] = self._storage_class
        if self._expiry is not None:
            rhdr = 'ongoing-request="false", expiry-date="{0}"'
            res['x-amz-restore'] = rhdr.format(self.expiry_date)

        if self._is_versioned:
            res['x-amz-version-id'] = str(self.version_id)

        if self.website_redirect_location:
            res['x-amz-website-redirect-location'] = self.website_redirect_location

        return res

    @property
    def size(self):
        return len(self.value)

    @property
    def storage_class(self):
        return self._storage_class

    @property
    def expiry_date(self):
        if self._expiry is not None:
            return self._expiry.strftime("%a, %d %b %Y %H:%M:%S GMT")


class FakeMultipart(BaseModel):

    def __init__(self, key_name, metadata):
        self.key_name = key_name
        self.metadata = metadata
        self.parts = {}
        self.partlist = []  # ordered list of part ID's
        rand_b64 = base64.b64encode(os.urandom(UPLOAD_ID_BYTES))
        self.id = rand_b64.decode('utf-8').replace('=', '').replace('+', '')

    def complete(self, body):
        decode_hex = codecs.getdecoder("hex_codec")
        total = bytearray()
        md5s = bytearray()

        last = None
        count = 0
        for pn, etag in body:
            part = self.parts.get(pn)
            if part is None or part.etag != etag:
                raise InvalidPart()
            if last is not None and len(last.value) < UPLOAD_PART_MIN_SIZE:
                raise EntityTooSmall()
            part_etag = part.etag.replace('"', '')
            md5s.extend(decode_hex(part_etag)[0])
            total.extend(part.value)
            last = part
            count += 1

        etag = hashlib.md5()
        etag.update(bytes(md5s))
        return total, "{0}-{1}".format(etag.hexdigest(), count)

    def set_part(self, part_id, value):
        if part_id < 1:
            return

        key = FakeKey(part_id, value)
        self.parts[part_id] = key
        if part_id not in self.partlist:
            insort(self.partlist, part_id)
        return key

    def list_parts(self):
        for part_id in self.partlist:
            yield self.parts[part_id]


class FakeGrantee(BaseModel):

    def __init__(self, id='', uri='', display_name=''):
        self.id = id
        self.uri = uri
        self.display_name = display_name

    def __eq__(self, other):
        if not isinstance(other, FakeGrantee):
            return False
        return self.id == other.id and self.uri == other.uri and self.display_name == other.display_name

    @property
    def type(self):
        return 'Group' if self.uri else 'CanonicalUser'

    def __repr__(self):
        return "FakeGrantee(display_name: '{}', id: '{}', uri: '{}')".format(self.display_name, self.id, self.uri)


ALL_USERS_GRANTEE = FakeGrantee(
    uri='http://acs.amazonaws.com/groups/global/AllUsers')
AUTHENTICATED_USERS_GRANTEE = FakeGrantee(
    uri='http://acs.amazonaws.com/groups/global/AuthenticatedUsers')
LOG_DELIVERY_GRANTEE = FakeGrantee(
    uri='http://acs.amazonaws.com/groups/s3/LogDelivery')

PERMISSION_FULL_CONTROL = 'FULL_CONTROL'
PERMISSION_WRITE = 'WRITE'
PERMISSION_READ = 'READ'
PERMISSION_WRITE_ACP = 'WRITE_ACP'
PERMISSION_READ_ACP = 'READ_ACP'


class FakeGrant(BaseModel):

    def __init__(self, grantees, permissions):
        self.grantees = grantees
        self.permissions = permissions

    def __repr__(self):
        return "FakeGrant(grantees: {}, permissions: {})".format(self.grantees, self.permissions)


class FakeAcl(BaseModel):

    def __init__(self, grants=[]):
        self.grants = grants

    @property
    def public_read(self):
        for grant in self.grants:
            if ALL_USERS_GRANTEE in grant.grantees:
                if PERMISSION_READ in grant.permissions:
                    return True
                if PERMISSION_FULL_CONTROL in grant.permissions:
                    return True
        return False

    def __repr__(self):
        return "FakeAcl(grants: {})".format(self.grants)


def get_canned_acl(acl):
    owner_grantee = FakeGrantee(
        id='75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a')
    grants = [FakeGrant([owner_grantee], [PERMISSION_FULL_CONTROL])]
    if acl == 'private':
        pass  # no other permissions
    elif acl == 'public-read':
        grants.append(FakeGrant([ALL_USERS_GRANTEE], [PERMISSION_READ]))
    elif acl == 'public-read-write':
        grants.append(FakeGrant([ALL_USERS_GRANTEE], [
                      PERMISSION_READ, PERMISSION_WRITE]))
    elif acl == 'authenticated-read':
        grants.append(
            FakeGrant([AUTHENTICATED_USERS_GRANTEE], [PERMISSION_READ]))
    elif acl == 'bucket-owner-read':
        pass  # TODO: bucket owner ACL
    elif acl == 'bucket-owner-full-control':
        pass  # TODO: bucket owner ACL
    elif acl == 'aws-exec-read':
        pass  # TODO: bucket owner, EC2 Read
    elif acl == 'log-delivery-write':
        grants.append(FakeGrant([LOG_DELIVERY_GRANTEE], [
                      PERMISSION_READ_ACP, PERMISSION_WRITE]))
    else:
        assert False, 'Unknown canned acl: %s' % (acl,)
    return FakeAcl(grants=grants)


class FakeTagging(BaseModel):

    def __init__(self, tag_set=None):
        self.tag_set = tag_set or FakeTagSet()


class FakeTagSet(BaseModel):

    def __init__(self, tags=None):
        self.tags = tags or []


class FakeTag(BaseModel):

    def __init__(self, key, value=None):
        self.key = key
        self.value = value


class LifecycleRule(BaseModel):

    def __init__(self, id=None, prefix=None, status=None, expiration_days=None,
                 expiration_date=None, transition_days=None,
                 transition_date=None, storage_class=None):
        self.id = id
        self.prefix = prefix
        self.status = status
        self.expiration_days = expiration_days
        self.expiration_date = expiration_date
        self.transition_days = transition_days
        self.transition_date = transition_date
        self.storage_class = storage_class


class CorsRule(BaseModel):

    def __init__(self, allowed_methods, allowed_origins, allowed_headers=None, expose_headers=None,
                 max_age_seconds=None):
        self.allowed_methods = [allowed_methods] if isinstance(allowed_methods, six.string_types) else allowed_methods
        self.allowed_origins = [allowed_origins] if isinstance(allowed_origins, six.string_types) else allowed_origins
        self.allowed_headers = [allowed_headers] if isinstance(allowed_headers, six.string_types) else allowed_headers
        self.exposed_headers = [expose_headers] if isinstance(expose_headers, six.string_types) else expose_headers
        self.max_age_seconds = max_age_seconds


class FakeBucket(BaseModel):

    def __init__(self, name, region_name):
        self.name = name
        self.region_name = region_name
        self.keys = _VersionedKeyStore()
        self.multiparts = {}
        self.versioning_status = None
        self.rules = []
        self.policy = None
        self.website_configuration = None
        self.acl = get_canned_acl('private')
        self.tags = FakeTagging()
        self.cors = []
        self.logging = {}

    @property
    def location(self):
        return self.region_name

    @property
    def is_versioned(self):
        return self.versioning_status == 'Enabled'

    def set_lifecycle(self, rules):
        self.rules = []
        for rule in rules:
            expiration = rule.get('Expiration')
            transition = rule.get('Transition')
            self.rules.append(LifecycleRule(
                id=rule.get('ID'),
                prefix=rule.get('Prefix'),
                status=rule['Status'],
                expiration_days=expiration.get('Days') if expiration else None,
                expiration_date=expiration.get('Date') if expiration else None,
                transition_days=transition.get('Days') if transition else None,
                transition_date=transition.get('Date') if transition else None,
                storage_class=transition[
                    'StorageClass'] if transition else None,
            ))

    def delete_lifecycle(self):
        self.rules = []

    def set_cors(self, rules):
        from moto.s3.exceptions import InvalidRequest, MalformedXML
        self.cors = []

        if len(rules) > 100:
            raise MalformedXML()

        for rule in rules:
            assert isinstance(rule["AllowedMethod"], list) or isinstance(rule["AllowedMethod"], six.string_types)
            assert isinstance(rule["AllowedOrigin"], list) or isinstance(rule["AllowedOrigin"], six.string_types)
            assert isinstance(rule.get("AllowedHeader", []), list) or isinstance(rule.get("AllowedHeader", ""),
                                                                                 six.string_types)
            assert isinstance(rule.get("ExposedHeader", []), list) or isinstance(rule.get("ExposedHeader", ""),
                                                                                 six.string_types)
            assert isinstance(rule.get("MaxAgeSeconds", "0"), six.string_types)

            if isinstance(rule["AllowedMethod"], six.string_types):
                methods = [rule["AllowedMethod"]]
            else:
                methods = rule["AllowedMethod"]

            for method in methods:
                if method not in ["GET", "PUT", "HEAD", "POST", "DELETE"]:
                    raise InvalidRequest(method)

            self.cors.append(CorsRule(
                rule["AllowedMethod"],
                rule["AllowedOrigin"],
                rule.get("AllowedHeader"),
                rule.get("ExposedHeader"),
                rule.get("MaxAgeSecond")
            ))

    def delete_cors(self):
        self.cors = []

    def set_tags(self, tagging):
        self.tags = tagging

    def delete_tags(self):
        self.tags = FakeTagging()

    @property
    def tagging(self):
        return self.tags

    def set_logging(self, logging_config, bucket_backend):
        if not logging_config:
            self.logging = {}
        else:
            from moto.s3.exceptions import InvalidTargetBucketForLogging, CrossLocationLoggingProhibitted
            # Target bucket must exist in the same account (assuming all moto buckets are in the same account):
            if not bucket_backend.buckets.get(logging_config["TargetBucket"]):
                raise InvalidTargetBucketForLogging("The target bucket for logging does not exist.")

            # Does the target bucket have the log-delivery WRITE and READ_ACP permissions?
            write = read_acp = False
            for grant in bucket_backend.buckets[logging_config["TargetBucket"]].acl.grants:
                # Must be granted to: http://acs.amazonaws.com/groups/s3/LogDelivery
                for grantee in grant.grantees:
                    if grantee.uri == "http://acs.amazonaws.com/groups/s3/LogDelivery":
                        if "WRITE" in grant.permissions or "FULL_CONTROL" in grant.permissions:
                            write = True

                        if "READ_ACP" in grant.permissions or "FULL_CONTROL" in grant.permissions:
                            read_acp = True

                        break

            if not write or not read_acp:
                raise InvalidTargetBucketForLogging("You must give the log-delivery group WRITE and READ_ACP"
                                                    " permissions to the target bucket")

            # Buckets must also exist within the same region:
            if bucket_backend.buckets[logging_config["TargetBucket"]].region_name != self.region_name:
                raise CrossLocationLoggingProhibitted()

            # Checks pass -- set the logging config:
            self.logging = logging_config

    def set_website_configuration(self, website_configuration):
        self.website_configuration = website_configuration

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'DomainName':
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "DomainName" ]"')
        elif attribute_name == 'WebsiteURL':
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "WebsiteURL" ]"')
        raise UnformattedGetAttTemplateException()

    def set_acl(self, acl):
        self.acl = acl

    @property
    def physical_resource_id(self):
        return self.name

    @classmethod
    def create_from_cloudformation_json(
            cls, resource_name, cloudformation_json, region_name):
        bucket = s3_backend.create_bucket(resource_name, region_name)
        return bucket


class S3Backend(BaseBackend):

    def __init__(self):
        self.buckets = {}

    def create_bucket(self, bucket_name, region_name):
        if bucket_name in self.buckets:
            raise BucketAlreadyExists(bucket=bucket_name)
        new_bucket = FakeBucket(name=bucket_name, region_name=region_name)
        self.buckets[bucket_name] = new_bucket
        return new_bucket

    def get_all_buckets(self):
        return self.buckets.values()

    def get_bucket(self, bucket_name):
        try:
            return self.buckets[bucket_name]
        except KeyError:
            raise MissingBucket(bucket=bucket_name)

    def delete_bucket(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        if bucket.keys:
            # Can't delete a bucket with keys
            return False
        else:
            return self.buckets.pop(bucket_name)

    def set_bucket_versioning(self, bucket_name, status):
        self.get_bucket(bucket_name).versioning_status = status

    def get_bucket_versioning(self, bucket_name):
        return self.get_bucket(bucket_name).versioning_status

    def get_bucket_latest_versions(self, bucket_name):
        versions = self.get_bucket_versions(bucket_name)
        maximum_version_per_key = {}
        latest_versions = {}

        for version in versions:
            if isinstance(version, FakeDeleteMarker):
                name = version.key.name
            else:
                name = version.name
            version_id = version.version_id
            maximum_version_per_key[name] = max(
                version_id,
                maximum_version_per_key.get(name, -1)
            )
            if version_id == maximum_version_per_key[name]:
                latest_versions[name] = version_id

        return latest_versions

    def get_bucket_versions(self, bucket_name, delimiter=None,
                            encoding_type=None,
                            key_marker=None,
                            max_keys=None,
                            version_id_marker=None,
                            prefix=''):
        bucket = self.get_bucket(bucket_name)

        if any((delimiter, encoding_type, key_marker, version_id_marker)):
            raise NotImplementedError(
                "Called get_bucket_versions with some of delimiter, encoding_type, key_marker, version_id_marker")

        return itertools.chain(*(l for key, l in bucket.keys.iterlists() if key.startswith(prefix)))

    def get_bucket_policy(self, bucket_name):
        return self.get_bucket(bucket_name).policy

    def set_bucket_policy(self, bucket_name, policy):
        self.get_bucket(bucket_name).policy = policy

    def delete_bucket_policy(self, bucket_name, body):
        bucket = self.get_bucket(bucket_name)
        bucket.policy = None

    def set_bucket_lifecycle(self, bucket_name, rules):
        bucket = self.get_bucket(bucket_name)
        bucket.set_lifecycle(rules)

    def set_bucket_website_configuration(self, bucket_name, website_configuration):
        bucket = self.get_bucket(bucket_name)
        bucket.set_website_configuration(website_configuration)

    def get_bucket_website_configuration(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return bucket.website_configuration

    def set_key(self, bucket_name, key_name, value, storage=None, etag=None):
        key_name = clean_key_name(key_name)

        bucket = self.get_bucket(bucket_name)

        old_key = bucket.keys.get(key_name, None)
        if old_key is not None and bucket.is_versioned:
            new_version_id = old_key._version_id + 1
        else:
            new_version_id = 0

        new_key = FakeKey(
            name=key_name,
            value=value,
            storage=storage,
            etag=etag,
            is_versioned=bucket.is_versioned,
            version_id=new_version_id)
        bucket.keys[key_name] = new_key

        return new_key

    def append_to_key(self, bucket_name, key_name, value):
        key_name = clean_key_name(key_name)

        key = self.get_key(bucket_name, key_name)
        key.append_to_value(value)
        return key

    def get_key(self, bucket_name, key_name, version_id=None):
        key_name = clean_key_name(key_name)
        bucket = self.get_bucket(bucket_name)
        key = None

        if bucket:
            if version_id is None:
                if key_name in bucket.keys:
                    key = bucket.keys[key_name]
            else:
                for key_version in bucket.keys.getlist(key_name):
                    if str(key_version.version_id) == str(version_id):
                        key = key_version
                        break

        if isinstance(key, FakeKey):
            return key
        else:
            return None

    def set_key_tagging(self, bucket_name, key_name, tagging):
        key = self.get_key(bucket_name, key_name)
        if key is None:
            raise MissingKey(key_name)
        key.set_tagging(tagging)
        return key

    def put_bucket_tagging(self, bucket_name, tagging):
        bucket = self.get_bucket(bucket_name)
        bucket.set_tags(tagging)

    def delete_bucket_tagging(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        bucket.delete_tags()

    def put_bucket_cors(self, bucket_name, cors_rules):
        bucket = self.get_bucket(bucket_name)
        bucket.set_cors(cors_rules)

    def put_bucket_logging(self, bucket_name, logging_config):
        bucket = self.get_bucket(bucket_name)
        bucket.set_logging(logging_config, self)

    def delete_bucket_cors(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        bucket.delete_cors()

    def initiate_multipart(self, bucket_name, key_name, metadata):
        bucket = self.get_bucket(bucket_name)
        new_multipart = FakeMultipart(key_name, metadata)
        bucket.multiparts[new_multipart.id] = new_multipart

        return new_multipart

    def complete_multipart(self, bucket_name, multipart_id, body):
        bucket = self.get_bucket(bucket_name)
        multipart = bucket.multiparts[multipart_id]
        value, etag = multipart.complete(body)
        if value is None:
            return
        del bucket.multiparts[multipart_id]

        key = self.set_key(bucket_name, multipart.key_name, value, etag=etag)
        key.set_metadata(multipart.metadata)
        return key

    def cancel_multipart(self, bucket_name, multipart_id):
        bucket = self.get_bucket(bucket_name)
        del bucket.multiparts[multipart_id]

    def list_multipart(self, bucket_name, multipart_id):
        bucket = self.get_bucket(bucket_name)
        return list(bucket.multiparts[multipart_id].list_parts())

    def get_all_multiparts(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return bucket.multiparts

    def set_part(self, bucket_name, multipart_id, part_id, value):
        bucket = self.get_bucket(bucket_name)
        multipart = bucket.multiparts[multipart_id]
        return multipart.set_part(part_id, value)

    def copy_part(self, dest_bucket_name, multipart_id, part_id,
                  src_bucket_name, src_key_name, start_byte, end_byte):
        src_key_name = clean_key_name(src_key_name)
        src_bucket = self.get_bucket(src_bucket_name)
        dest_bucket = self.get_bucket(dest_bucket_name)
        multipart = dest_bucket.multiparts[multipart_id]
        src_value = src_bucket.keys[src_key_name].value
        if start_byte is not None:
            src_value = src_value[start_byte:end_byte + 1]
        return multipart.set_part(part_id, src_value)

    def prefix_query(self, bucket, prefix, delimiter):
        key_results = set()
        folder_results = set()
        if prefix:
            for key_name, key in bucket.keys.items():
                if key_name.startswith(prefix):
                    key_without_prefix = key_name.replace(prefix, "", 1)
                    if delimiter and delimiter in key_without_prefix:
                        # If delimiter, we need to split out folder_results
                        key_without_delimiter = key_without_prefix.split(delimiter)[
                            0]
                        folder_results.add("{0}{1}{2}".format(
                            prefix, key_without_delimiter, delimiter))
                    else:
                        key_results.add(key)
        else:
            for key_name, key in bucket.keys.items():
                if delimiter and delimiter in key_name:
                    # If delimiter, we need to split out folder_results
                    folder_results.add(key_name.split(
                        delimiter)[0] + delimiter)
                else:
                    key_results.add(key)

        key_results = filter(lambda key: not isinstance(key, FakeDeleteMarker), key_results)
        key_results = sorted(key_results, key=lambda key: key.name)
        folder_results = [folder_name for folder_name in sorted(
            folder_results, key=lambda key: key)]

        return key_results, folder_results

    def _set_delete_marker(self, bucket_name, key_name):
        bucket = self.get_bucket(bucket_name)
        bucket.keys[key_name] = FakeDeleteMarker(
            key=bucket.keys[key_name]
        )

    def delete_key(self, bucket_name, key_name, version_id=None):
        key_name = clean_key_name(key_name)
        bucket = self.get_bucket(bucket_name)

        try:
            if not bucket.is_versioned:
                bucket.keys.pop(key_name)
            else:
                if version_id is None:
                    self._set_delete_marker(bucket_name, key_name)
                else:
                    if key_name not in bucket.keys:
                        raise KeyError
                    bucket.keys.setlist(
                        key_name,
                        [
                            key
                            for key in bucket.keys.getlist(key_name)
                            if str(key.version_id) != str(version_id)
                        ]
                    )
            return True
        except KeyError:
            return False

    def copy_key(self, src_bucket_name, src_key_name, dest_bucket_name,
                 dest_key_name, storage=None, acl=None, src_version_id=None):
        src_key_name = clean_key_name(src_key_name)
        dest_key_name = clean_key_name(dest_key_name)
        dest_bucket = self.get_bucket(dest_bucket_name)
        key = self.get_key(src_bucket_name, src_key_name,
                           version_id=src_version_id)
        if dest_key_name != src_key_name:
            key = key.copy(dest_key_name)
        dest_bucket.keys[dest_key_name] = key

        # By this point, the destination key must exist, or KeyError
        if dest_bucket.is_versioned:
            dest_bucket.keys[dest_key_name].increment_version()
        if storage is not None:
            key.set_storage_class(storage)
        if acl is not None:
            key.set_acl(acl)

    def set_bucket_acl(self, bucket_name, acl):
        bucket = self.get_bucket(bucket_name)
        bucket.set_acl(acl)

    def get_bucket_acl(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return bucket.acl


s3_backend = S3Backend()
