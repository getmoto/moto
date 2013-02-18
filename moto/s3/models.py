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
        self.keys = []


class S3Backend(BaseBackend):
    base_url = "https://(.+).s3.amazonaws.com"

    def __init__(self):
        self.buckets = {}

    def create_bucket(self, bucket_name):
        new_bucket = FakeBucket(name=bucket_name)
        self.buckets[bucket_name] = new_bucket
        return new_bucket

    def get_bucket(self, bucket_name):
        return self.buckets.get(bucket_name)

    def set_key(self, bucket_name, key_name, value):
        bucket = self.buckets[bucket_name]
        new_key = FakeKey(name=key_name, value=value)
        bucket.keys.append(new_key)

        return new_key

    def get_key(self, bucket_name, key_name):
        bucket = self.buckets[bucket_name]
        found_key = None
        for key in bucket.keys:
            if key.name == key_name:
                found_key = key
                break

        return found_key


s3_backend = S3Backend()
