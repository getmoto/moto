# from boto.s3.bucket import Bucket
# from boto.s3.key import Key
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

class FakeBucket(object):
    def __init__(self, name):
        self.name = name
        self.keys = {}


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
        bucket = self.buckets[bucket_name]
        return bucket.keys.get(key_name)

    def delete_key(self, bucket_name, key_name):
        bucket = self.buckets[bucket_name]
        return bucket.keys.pop(key_name)

    def copy_key(self, src_bucket_name, src_key_name, dest_bucket_name, dest_key_name):
        src_bucket = self.buckets[src_bucket_name]
        dest_bucket = self.buckets[dest_bucket_name]
        dest_bucket.keys[dest_key_name] = src_bucket.keys[src_key_name]

s3_backend = S3Backend()
