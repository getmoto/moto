import datetime
import md5

from moto.core import BaseBackend


class FakeKey(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.last_modified = datetime.datetime.now()

    @property
    def etag(self):
        value_md5 = md5.new()
        value_md5.update(self.value)
        return '"{0}"'.format(value_md5.hexdigest())

    @property
    def last_modified_ISO8601(self):
        return self.last_modified.strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def last_modified_RFC1123(self):
        # Different datetime formats depending on how the key is obtained
        # https://github.com/boto/boto/issues/466
        RFC1123 = '%a, %d %b %Y %H:%M:%S GMT'
        return self.last_modified.strftime(RFC1123)

    @property
    def response_dict(self):
        return {
            'etag': self.etag,
            'last-modified': self.last_modified_RFC1123,
        }

    @property
    def size(self):
        return len(self.value)


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
        bucket = self.get_bucket(bucket_name)
        if bucket:
            return bucket.keys.get(key_name)

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
