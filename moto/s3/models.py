import os
import base64
import datetime
import hashlib
import copy
import itertools

from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime, rfc_1123_datetime
from .exceptions import BucketAlreadyExists, MissingBucket
from .utils import clean_key_name, _VersionedKeyStore

UPLOAD_ID_BYTES = 43
UPLOAD_PART_MIN_SIZE = 5242880


class FakeKey(object):

    def __init__(self, name, value, storage="STANDARD", etag=None, is_versioned=False, version_id=0):
        self.name = name
        self.value = value
        self.last_modified = datetime.datetime.now()
        self._storage_class = storage
        self._metadata = {}
        self._expiry = None
        self._etag = etag
        self._version_id = version_id
        self._is_versioned = is_versioned

    def copy(self, new_name=None):
        r = copy.deepcopy(self)
        if new_name is not None:
            r.name = new_name
        return r

    def set_metadata(self, key, metadata):
        self._metadata[key] = metadata

    def clear_metadata(self):
        self._metadata = {}

    def set_storage_class(self, storage_class):
        self._storage_class = storage_class

    def append_to_value(self, value):
        self.value += value
        self.last_modified = datetime.datetime.now()
        self._etag = None  # must recalculate etag
        if self._is_versioned:
            self._version_id += 1
        else:
            self._is_versioned = 0

    def restore(self, days):
        self._expiry = datetime.datetime.now() + datetime.timedelta(days)

    @property
    def etag(self):
        if self._etag is None:
            value_md5 = hashlib.md5()
            value_md5.update(bytes(self.value))
            self._etag = value_md5.hexdigest()
        return '"{0}"'.format(self._etag)

    @property
    def last_modified_ISO8601(self):
        return iso_8601_datetime(self.last_modified)

    @property
    def last_modified_RFC1123(self):
        # Different datetime formats depending on how the key is obtained
        # https://github.com/boto/boto/issues/466
        return rfc_1123_datetime(self.last_modified)

    @property
    def metadata(self):
        return self._metadata

    @property
    def response_dict(self):
        r = {
            'etag': self.etag,
            'last-modified': self.last_modified_RFC1123,
        }
        if self._storage_class != 'STANDARD':
            r['x-amz-storage-class'] = self._storage_class
        if self._expiry is not None:
            rhdr = 'ongoing-request="false", expiry-date="{0}"'
            r['x-amz-restore'] = rhdr.format(self.expiry_date)

        if self._is_versioned:
            r['x-amz-version-id'] = self._version_id

        return r

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


class FakeMultipart(object):
    def __init__(self, key_name):
        self.key_name = key_name
        self.parts = {}
        self.id = base64.b64encode(os.urandom(UPLOAD_ID_BYTES)).replace('=', '').replace('+', '')

    def complete(self):
        total = bytearray()
        md5s = bytearray()
        last_part_name = len(self.list_parts())

        for part in self.list_parts():
            if part.name != last_part_name and len(part.value) < UPLOAD_PART_MIN_SIZE:
                return None, None
            md5s.extend(part.etag.replace('"', '').decode('hex'))
            total.extend(part.value)

        etag = hashlib.md5()
        etag.update(bytes(md5s))
        return total, "{0}-{1}".format(etag.hexdigest(), last_part_name)

    def set_part(self, part_id, value):
        if part_id < 1:
            return

        key = FakeKey(part_id, value)
        self.parts[part_id] = key
        return key

    def list_parts(self):
        parts = []

        for part_id, index in enumerate(sorted(self.parts.keys()), start=1):
            # Make sure part ids are continuous
            if part_id != index:
                return
            parts.append(self.parts[part_id])

        return parts


class FakeBucket(object):

    def __init__(self, name):
        self.name = name
        self.keys = _VersionedKeyStore()
        self.multiparts = {}
        self.versioning_status = None

    @property
    def is_versioned(self):
        return self.versioning_status == 'Enabled'


class S3Backend(BaseBackend):

    def __init__(self):
        self.buckets = {}

    def create_bucket(self, bucket_name):
        if bucket_name in self.buckets:
            raise BucketAlreadyExists()
        new_bucket = FakeBucket(name=bucket_name)
        self.buckets[bucket_name] = new_bucket
        return new_bucket

    def get_all_buckets(self):
        return self.buckets.values()

    def get_bucket(self, bucket_name):
        try:
            return self.buckets[bucket_name]
        except KeyError:
            raise MissingBucket()

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

    def get_bucket_versions(self, bucket_name, delimiter=None,
                            encoding_type=None,
                            key_marker=None,
                            max_keys=None,
                            version_id_marker=None):
        bucket = self.get_bucket(bucket_name)

        if any((delimiter, encoding_type, key_marker, version_id_marker)):
            raise NotImplementedError(
                "Called get_bucket_versions with some of delimiter, encoding_type, key_marker, version_id_marker")

        return itertools.chain(*(l for _, l in bucket.keys.iterlists()))

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
        if bucket:
            if version_id is None:
                return bucket.keys.get(key_name)
            else:
                for key in bucket.keys.getlist(key_name):
                    if str(key._version_id) == str(version_id):
                        return key

    def initiate_multipart(self, bucket_name, key_name):
        bucket = self.get_bucket(bucket_name)
        new_multipart = FakeMultipart(key_name)
        bucket.multiparts[new_multipart.id] = new_multipart

        return new_multipart

    def complete_multipart(self, bucket_name, multipart_id):
        bucket = self.get_bucket(bucket_name)
        multipart = bucket.multiparts[multipart_id]
        value, etag = multipart.complete()
        if value is None:
            return
        del bucket.multiparts[multipart_id]

        return self.set_key(bucket_name, multipart.key_name, value, etag=etag)

    def cancel_multipart(self, bucket_name, multipart_id):
        bucket = self.get_bucket(bucket_name)
        del bucket.multiparts[multipart_id]

    def list_multipart(self, bucket_name, multipart_id):
        bucket = self.get_bucket(bucket_name)
        return bucket.multiparts[multipart_id].list_parts()

    def get_all_multiparts(self, bucket_name):
        bucket = self.get_bucket(bucket_name)
        return bucket.multiparts

    def set_part(self, bucket_name, multipart_id, part_id, value):
        bucket = self.get_bucket(bucket_name)
        multipart = bucket.multiparts[multipart_id]
        return multipart.set_part(part_id, value)

    def copy_part(self, dest_bucket_name, multipart_id, part_id,
                  src_bucket_name, src_key_name):
        src_key_name = clean_key_name(src_key_name)
        src_bucket = self.get_bucket(src_bucket_name)
        dest_bucket = self.get_bucket(dest_bucket_name)
        multipart = dest_bucket.multiparts[multipart_id]
        return multipart.set_part(part_id, src_bucket.keys[src_key_name].value)

    def prefix_query(self, bucket, prefix, delimiter):
        key_results = set()
        folder_results = set()
        if prefix:
            for key_name, key in bucket.keys.iteritems():
                if key_name.startswith(prefix):
                    key_without_prefix = key_name.replace(prefix, "", 1)
                    if delimiter and delimiter in key_without_prefix:
                        # If delimiter, we need to split out folder_results
                        key_without_delimiter = key_without_prefix.split(delimiter)[0]
                        folder_results.add("{0}{1}{2}".format(prefix, key_without_delimiter, delimiter))
                    else:
                        key_results.add(key)
        else:
            for key_name, key in bucket.keys.iteritems():
                if delimiter and delimiter in key_name:
                    # If delimiter, we need to split out folder_results
                    folder_results.add(key_name.split(delimiter)[0])
                else:
                    key_results.add(key)

        key_results = sorted(key_results, key=lambda key: key.name)
        folder_results = [folder_name for folder_name in sorted(folder_results, key=lambda key: key)]

        return key_results, folder_results

    def delete_key(self, bucket_name, key_name):
        key_name = clean_key_name(key_name)
        bucket = self.get_bucket(bucket_name)
        return bucket.keys.pop(key_name)

    def copy_key(self, src_bucket_name, src_key_name, dest_bucket_name, dest_key_name, storage=None):
        src_key_name = clean_key_name(src_key_name)
        dest_key_name = clean_key_name(dest_key_name)
        src_bucket = self.get_bucket(src_bucket_name)
        dest_bucket = self.get_bucket(dest_bucket_name)
        key = src_bucket.keys[src_key_name]
        if dest_key_name != src_key_name:
            key = key.copy(dest_key_name)
        dest_bucket.keys[dest_key_name] = key
        if storage is not None:
            dest_bucket.keys[dest_key_name].set_storage_class(storage)

s3_backend = S3Backend()
