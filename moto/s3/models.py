# from boto.s3.bucket import Bucket
# from boto.s3.key import Key
import os
import base64
import md5

from moto.core import BaseBackend


class FakeKey(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    @property
    def etag(self):
        value_md5 = md5.new()
        value_md5.update(self.value)
        return '"{0}"'.format(value_md5.hexdigest())

    @property
    def size(self):
        return len(self.value)


class FakeMultipart(object):
    def __init__(self, key_name):
        self.key_name = key_name
        self.parts = {}
        self.id = base64.b64encode(os.urandom(43)).replace('=', '')

    def complete(self):
        total = bytearray()

        for part_id, index in enumerate(sorted(self.parts.keys()), start=1):
            # Make sure part ids are continuous
            if part_id != index:
                return

            total.extend(self.parts[part_id].value)

        if len(total) < 5242880:
            return

        return total

    def set_part(self, part_id, value):
        if part_id < 1:
            return

        key = FakeKey(part_id, value)
        self.parts[part_id] = key
        return key


class FakeBucket(object):
    def __init__(self, name):
        self.name = name
        self.keys = {}
        self.multiparts = {}


class S3Backend(BaseBackend):

    def __init__(self):
        self.buckets = {}

    def create_bucket(self, bucket_name):
        new_bucket = FakeBucket(name=bucket_name)
        self.buckets[bucket_name] = new_bucket
        return new_bucket

    def get_all_buckets(self):
        return self.buckets.values()

    def get_bucket(self, bucket_name):
        return self.buckets.get(bucket_name)

    def delete_bucket(self, bucket_name):
        bucket = self.buckets.get(bucket_name)
        if bucket:
            if bucket.keys:
                # Can't delete a bucket with keys
                return False
            else:
                return self.buckets.pop(bucket_name)
        return None

    def set_key(self, bucket_name, key_name, value):
        bucket = self.buckets[bucket_name]
        new_key = FakeKey(name=key_name, value=value)
        bucket.keys[key_name] = new_key

        return new_key

    def get_key(self, bucket_name, key_name):
        bucket = self.get_bucket(bucket_name)
        if bucket:
            return bucket.keys.get(key_name)

    def initiate_multipart(self, bucket_name, key_name):
        bucket = self.buckets[bucket_name]
        new_multipart = FakeMultipart(key_name)
        bucket.multiparts[new_multipart.id] = new_multipart

        return new_multipart

    def complete_multipart(self, bucket_name, multipart_id):
        bucket = self.buckets[bucket_name]
        multipart = bucket.multiparts[multipart_id]
        value = multipart.complete()
        if value is None:
            return
        del bucket.multiparts[multipart_id]

        return self.set_key(bucket_name, multipart.key_name, value)

    def set_part(self, bucket_name, multipart_id, part_id, value):
        bucket = self.buckets[bucket_name]
        multipart = bucket.multiparts[multipart_id]
        return multipart.set_part(part_id, value)

    def prefix_query(self, bucket, prefix):
        key_results = set()
        folder_results = set()
        if prefix:
            for key_name, key in bucket.keys.iteritems():
                if key_name.startswith(prefix):
                    if '/' in key_name.lstrip(prefix):
                        key_without_prefix = key_name.lstrip(prefix).split("/")[0]
                        folder_results.add("{}{}".format(prefix, key_without_prefix))
                    else:
                        key_results.add(key)
        else:
            for key_name, key in bucket.keys.iteritems():
                if '/' in key_name:
                    folder_results.add(key_name.split("/")[0])
                else:
                    key_results.add(key)

        key_results = sorted(key_results, key=lambda key: key.name)
        folder_results = [folder_name for folder_name in sorted(folder_results, key=lambda key: key)]

        return key_results, folder_results

    def delete_key(self, bucket_name, key_name):
        bucket = self.buckets[bucket_name]
        return bucket.keys.pop(key_name)

    def copy_key(self, src_bucket_name, src_key_name, dest_bucket_name, dest_key_name):
        src_bucket = self.buckets[src_bucket_name]
        dest_bucket = self.buckets[dest_bucket_name]
        dest_bucket.keys[dest_key_name] = src_bucket.keys[src_key_name]

s3_backend = S3Backend()
